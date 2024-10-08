import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { CoinsController } from './coins.controller';
import { CoinsService } from './coins.service';
import { Coin } from './coins.entity';
import { CoinData } from './entities/coin-data.entity';
import { LatestCoinData } from './entities/latest-coins.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Coin, CoinData, LatestCoinData])],
  controllers: [CoinsController],
  providers: [CoinsService],
  exports: [CoinsService],
})
export class CoinsModule {}
