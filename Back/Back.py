import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt


class Context:
    def __init__(self, context=None):
        if context is None:
            self.BktestParam = {
                # 'init_period': ['2005-03-01', '2018-01-31'],
                'commission_rate': 0,       # 手续费
                'signal': None,             # 交易信号函数
                'refresh_dates': None,      # 调仓日期序列
                'signal_params': {}         # 交易信号函数需要的额外参数
            }

            self.GlobalParam = {
                # 'data': None,  # 数据
                'asset_pool': None,         # 资产池
                'daily_close': None,        # 资产每日的收盘价
                'daily_dates': None,        # 交易日期序列
                'base_nav': None            # 基准的净值曲线
            }

            self.BktestResult = {
                'w': None,                  # 每个调仓日期的权重
                'nav': None,                # 回测的净值曲线
                'nav_perf': None,           # 回测表现
                'df': None                  # 回测结果
            }
        else:
            self.GlobalParam = context.GlobalParam
            self.BktestParam = context.BktestParam
            self.BktestResult = context.BktestResult

    def cal_long_weight(self):
        refresh_dates = []
        self.BktestResult['w'] = pd.DataFrame(columns=self.GlobalParam['asset_pool'])
        for date in self.GlobalParam['daily_dates']:
            sig, weight = self.BktestParam['signal'](self, date, **self.BktestParam['signal_params'])
            if sig:
                refresh_dates.append(date)
                self.BktestResult['w'].loc[date, :] = weight
                self.BktestResult['w'].loc[date, :].fillna(0, inplace=True)

        self.BktestParam['refresh_dates'] = refresh_dates
        return self.BktestResult['w']

    def cal_nav(self):
        close = self.GlobalParam['daily_close']
        w = self.BktestResult['w']
        commission_rate = self.BktestParam['commission_rate']
        daily_dates = self.GlobalParam['daily_dates']
        refresh_dates = self.BktestParam['refresh_dates']

        # 建仓
        nav = pd.Series(index=daily_dates)
        refresh_w = w.iloc[0, :]
        start_date = w.index.tolist()[0]
        nav[start_date] = 1 - commission_rate
        last_portfolio = np.asarray((1 - commission_rate) * refresh_w)
        for i in range(daily_dates.index(start_date) + 1, len(daily_dates)):
            # 执行净值更新，分空仓和不空仓情形
            if sum(last_portfolio) == 0:
                nav[i] = nav[i - 1]
            else:
                last_portfolio = np.asarray(close.iloc[i, :] / close.iloc[i - 1, :]) * last_portfolio
                nav[i] = np.nansum(last_portfolio)

            # 判断当前日期是否为新的调仓日，是则进行调仓
            if daily_dates[i] in refresh_dates:
                # 将最新仓位归一化
                last_w = np.zeros_like(last_portfolio) if np.nansum(last_portfolio) == 0 \
                    else last_portfolio

                # 获取最新的权重分布
                refresh_w = w.loc[daily_dates[i], :]

                # 根据前后权重差别计算换手率，调整净值
                refresh_turn = np.nansum(np.abs(refresh_w - last_w))
                nav[i] = nav[i] * (1 - refresh_turn * commission_rate)
                last_portfolio = np.asarray(nav[i] * refresh_w)

        self.BktestResult['nav'] = nav
        return nav
