import json
import time
import websocket
import gzip
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from db_manager import DBManager
import os


class CoinexWebSocket:
    def __init__(self, access_id, signed_str, db_manager):
        self.access_id = access_id
        self.signed_str = signed_str
        self.db_manager = db_manager
        self.next_update_time = datetime.now(
            timezone.utc
        )  # Initialize the update time first
        self.coins = self.update_coin_list()  # Now it's safe to call update_coin_list

    def authenticate_request(self, timestamp=None):
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        payload = {
            "method": "server.sign",
            "params": {
                "access_id": self.access_id,
                "signed_str": self.signed_str,
                "timestamp": timestamp,
            },
            "id": 1,
        }
        return json.dumps(payload)

    @staticmethod
    def decompress_message(compressed_message):
        decompressed_bytes = gzip.decompress(compressed_message)
        decompressed_str = decompressed_bytes.decode("utf-8")
        return json.loads(decompressed_str)

    def create_subscription_request(self, coins):
        payload = {
            "method": "bbo.subscribe",
            "params": {"market_list": coins},
            "id": 1,
        }
        return json.dumps(payload)

    def update_coin_list(self):
        if datetime.now(timezone.utc) >= self.next_update_time:
            query = "SELECT coin_name FROM coins_table;"
            result = self.db_manager.execute_query(query)
            self.coins = [coin[0] for coin in result]
            self.next_update_time += timedelta(
                days=1
            )  # Update the next time we need to refresh
            print(f"Coin list updated: {self.coins}")
        return self.coins  # Return the current list of coins

    def insert_data_into_db(self, parsed_data):
        try:
            timestamp = datetime.fromtimestamp(parsed_data["timestamp"] / 1000.0)
            query = "SELECT coin_id FROM coins_table WHERE coin_name = %s"
            coin_id = self.db_manager.execute_query(query, (parsed_data["symbol"],))
            if not coin_id:
                insert_coin_query = (
                    "INSERT INTO coins_table (coin_name) VALUES (%s) RETURNING coin_id"
                )
                coin_id = self.db_manager.execute_query(
                    insert_coin_query, (parsed_data["symbol"],)
                )
                coin_id = coin_id[0][0] if coin_id else None
            else:
                coin_id = coin_id[0][0]

            if coin_id:
                insert_data_query = """
                INSERT INTO coin_data_table (
                    coin_id, timestamp, best_bid, best_ask, best_bid_qty, best_ask_qty, mark_price, last_price, updated_at, exchange
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                self.db_manager.cursor.execute(
                    insert_data_query,
                    (
                        coin_id,
                        timestamp,
                        parsed_data["best_bid"],
                        parsed_data["best_ask"],
                        parsed_data["best_bid_qty"],
                        parsed_data["best_ask_qty"],
                        parsed_data["mark_price"],
                        parsed_data["last_price"],
                        timestamp,
                        "COINEX",
                    ),
                )
                self.db_manager.commit()
            else:
                print("Error: Could not find or insert coin_id")
        except Exception as e:
            print(f"Error inserting data into DB: {e}")

    def on_message(self, ws, message):
        parsed_msg = self.decompress_message(message)
        if "data" in parsed_msg:
            data = parsed_msg["data"]
            parsed_data = {
                "symbol": data["market"],
                "best_bid": data["best_bid_price"],
                "best_ask": data["best_ask_price"],
                "best_bid_qty": data["best_bid_size"],
                "best_ask_qty": data["best_ask_size"],
                "mark_price": None,
                "last_price": None,
                "timestamp": data["updated_at"],
            }
            try:
                self.insert_data_into_db(parsed_data)
            except Exception as e:
                print(f"Error inserting data into DB: {e, parsed_data}")

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket closed: {close_status_code}, {close_msg}")
        print("Reconnecting...")
        time.sleep(0.5)
        self.run()

    def on_open(self, ws):
        auth_message = self.authenticate_request()
        ws.send(auth_message)
        print(f"Sent authentication message: {auth_message}")
        coins = self.update_coin_list()
        subscription_message = self.create_subscription_request(coins)
        ws.send(subscription_message)
        print(f"Sent subscription message for coins: {coins}")

    def run(self):
        websocket_url = "wss://socket.coinex.com/v2/futures"
        ws = websocket.WebSocketApp(
            websocket_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        ws.run_forever()


if __name__ == "__main__":
    load_dotenv()
    db_manager = DBManager()
    access_id = os.getenv("APIKEYCOINEX")
    signed_str = os.getenv("APISECRETKEYCOINEX")
    coinex_ws = CoinexWebSocket(access_id, signed_str, db_manager)
    try:
        coinex_ws.run()
    finally:
        db_manager.close()
