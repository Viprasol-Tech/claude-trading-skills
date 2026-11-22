//+------------------------------------------------------------------+
//| EA_Template.mq5                                                  |
//| Part of claude-trading-skills by Viprasol Tech Private Limited.  |
//| A production-shaped MT5 Expert Advisor skeleton: EMA crossover    |
//| entries on closed bars, ATR stops, risk-based lots and the main   |
//| pre-trade checks the MQL5 Market validation expects (permissions, |
//| trade mode, stops level, volume step/min/max, free margin).       |
//| Educational template - test on a demo account before live use.   |
//+------------------------------------------------------------------+
#property copyright "Viprasol Tech Private Limited"
#property link      "https://viprasol.com"
#property version   "1.00"

#include <Trade\Trade.mqh>

//--- inputs
input group "Signal"
input int    InpFastPeriod   = 20;     // Fast EMA period
input int    InpSlowPeriod   = 50;     // Slow EMA period
input group "Risk"
input double InpRiskPercent  = 1.0;    // Risk per trade, % of equity
input int    InpAtrPeriod    = 14;     // ATR period for the stop
input double InpAtrStopMult  = 2.0;    // Stop distance = ATR x this
input double InpRewardRisk   = 2.0;    // Take profit = stop distance x this (0 = none)
input int    InpMaxSpread    = 30;     // Skip entries above this spread (points, 0 = off)
input double InpMaxDailyLoss = 3.0;    // Stop trading for the day after this % loss (0 = off)
input group "Execution"
input ulong  InpMagic        = 20260101; // Magic number (unique per EA instance)
input int    InpDeviation    = 10;     // Max slippage, points

//--- globals (reset in OnInit: they survive a timeframe/inputs change)
CTrade   trade;
int      g_fast = INVALID_HANDLE;
int      g_slow = INVALID_HANDLE;
int      g_atr  = INVALID_HANDLE;
datetime g_lastBar = 0;
datetime g_dayStart = 0;
double   g_dayStartEquity = 0.0;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpFastPeriod < 1 || InpSlowPeriod <= InpFastPeriod || InpAtrPeriod < 1 ||
      InpRiskPercent <= 0.0 || InpRiskPercent > 10.0 || InpAtrStopMult <= 0.0)
      return(INIT_PARAMETERS_INCORRECT);

   g_lastBar = 0;
   g_dayStart = 0;
   g_dayStartEquity = 0.0;

   g_fast = iMA(_Symbol, _Period, InpFastPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_slow = iMA(_Symbol, _Period, InpSlowPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_atr  = iATR(_Symbol, _Period, InpAtrPeriod);
   if(g_fast == INVALID_HANDLE || g_slow == INVALID_HANDLE || g_atr == INVALID_HANDLE)
     {
      PrintFormat("Indicator handle failed, error %d", GetLastError());
      return(INIT_FAILED);
     }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviation);
   trade.SetTypeFillingBySymbol(_Symbol);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(g_fast != INVALID_HANDLE) IndicatorRelease(g_fast);
   if(g_slow != INVALID_HANDLE) IndicatorRelease(g_slow);
   if(g_atr  != INVALID_HANDLE) IndicatorRelease(g_atr);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   if(!IsNewBar())
      return;                       // all decisions on closed bars only
   if(!TradingAllowed() || DailyLossHit())
      return;

   double fast[], slow[], atr[];
   ArraySetAsSeries(fast, true);
   ArraySetAsSeries(slow, true);
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_fast, 0, 1, 2, fast) != 2 ||
      CopyBuffer(g_slow, 0, 1, 2, slow) != 2 ||
      CopyBuffer(g_atr,  0, 1, 1, atr)  != 1)
      return;                       // indicator not ready yet

   // [0] = last closed bar, [1] = the bar before it
   bool crossUp   = fast[1] <= slow[1] && fast[0] > slow[0];
   bool crossDown = fast[1] >= slow[1] && fast[0] < slow[0];
   if(!crossUp && !crossDown)
      return;

   ENUM_POSITION_TYPE wanted = crossUp ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
   CloseOpposite(wanted);
   if(HasPosition())
      return;                       // one position per symbol per magic

   if(InpMaxSpread > 0 && SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpread)
      return;

   OpenPosition(wanted, atr[0] * InpAtrStopMult);
  }

//+------------------------------------------------------------------+
bool IsNewBar()
  {
   datetime t = iTime(_Symbol, _Period, 0);
   if(t == 0 || t == g_lastBar)
      return(false);
   bool first = (g_lastBar == 0);
   g_lastBar = t;
   return(!first);                  // skip the bar the EA was attached on
  }

//+------------------------------------------------------------------+
bool TradingAllowed()
  {
   // Live-only checks: the Strategy Tester has no terminal connection or buttons.
   if(!MQLInfoInteger(MQL_TESTER))
     {
      if(!TerminalInfoInteger(TERMINAL_CONNECTED))      return(false);
      if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))  return(false);
      if(!MQLInfoInteger(MQL_TRADE_ALLOWED))            return(false);
      if(!AccountInfoInteger(ACCOUNT_TRADE_EXPERT))     return(false);
      if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))    return(false);
     }
   ENUM_SYMBOL_TRADE_MODE mode = (ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE);
   return(mode != SYMBOL_TRADE_MODE_DISABLED && mode != SYMBOL_TRADE_MODE_CLOSEONLY);
  }

//+------------------------------------------------------------------+
bool SideAllowed(const bool isBuy)
  {
   ENUM_SYMBOL_TRADE_MODE mode = (ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE);
   if(isBuy && mode == SYMBOL_TRADE_MODE_SHORTONLY) return(false);
   if(!isBuy && mode == SYMBOL_TRADE_MODE_LONGONLY) return(false);
   return(true);
  }

//+------------------------------------------------------------------+
//| The day's starting equity is kept in terminal global variables so |
//| a restart or timeframe change mid-day does not reset the limit.   |
bool DailyLossHit()
  {
   if(InpMaxDailyLoss <= 0.0)
      return(false);
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   now.hour = 0; now.min = 0; now.sec = 0;
   datetime today = StructToTime(now);           // server-time midnight
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   if(today != g_dayStart)
     {
      string prefix = StringFormat("EAT_%s_%I64u_", _Symbol, InpMagic);
      string keyDay = prefix + "day", keyEq = prefix + "eq";
      if(GlobalVariableCheck(keyDay) && (datetime)GlobalVariableGet(keyDay) == today)
         g_dayStartEquity = GlobalVariableGet(keyEq);  // same day: keep the stored baseline
      else
        {
         g_dayStartEquity = equity;                     // new day: start a fresh baseline
         GlobalVariableSet(keyDay, (double)today);
         GlobalVariableSet(keyEq, equity);
        }
      g_dayStart = today;
     }
   return(g_dayStartEquity > 0.0 &&
          (g_dayStartEquity - equity) / g_dayStartEquity * 100.0 >= InpMaxDailyLoss);
  }

//+------------------------------------------------------------------+
//| Positions are matched by symbol AND magic (hedging-account safe) |
//+------------------------------------------------------------------+
bool HasPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return(true);
     }
   return(false);
  }

//+------------------------------------------------------------------+
void CloseOpposite(const ENUM_POSITION_TYPE wanted)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == wanted) continue;
      if(!trade.PositionClose(ticket) || !RetcodeOk(trade.ResultRetcode()))
         PrintFormat("Close %I64u failed: %u %s", ticket, trade.ResultRetcode(),
                     trade.ResultRetcodeDescription());
     }
  }

//+------------------------------------------------------------------+
void OpenPosition(const ENUM_POSITION_TYPE side, const double stopDistance)
  {
   bool   isBuy = (side == POSITION_TYPE_BUY);
   double ask   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = isBuy ? ask : bid;
   if(entry <= 0.0 || stopDistance <= 0.0 || !SideAllowed(isBuy))
      return;

   // Respect the broker's minimum stop distance. A buy's SL is measured from Bid
   // and a sell's from Ask, so add the spread to the distance from the entry price.
   double point    = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minDist  = (double)(SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) +
                              SymbolInfoInteger(_Symbol, SYMBOL_SPREAD)) * point;
   double dist     = MathMax(stopDistance, minDist + point);

   double sl = NormalizePrice(isBuy ? entry - dist : entry + dist);
   double tp = 0.0;
   if(InpRewardRisk > 0.0)
      tp = NormalizePrice(isBuy ? entry + dist * InpRewardRisk : entry - dist * InpRewardRisk);

   double lots = RiskLots(entry, sl);
   if(lots <= 0.0)
     {
      Print("Risk budget is below the minimum lot: trade skipped");
      return;
     }

   ENUM_ORDER_TYPE type = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double margin = 0.0;
   if(!OrderCalcMargin(type, _Symbol, lots, entry, margin) ||
      margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE))
     {
      PrintFormat("Not enough free margin for %.2f lots (needs %.2f)", lots, margin);
      return;
     }

   bool sent = isBuy ? trade.Buy(lots, _Symbol, ask, sl, tp, "EA_Template")
                     : trade.Sell(lots, _Symbol, bid, sl, tp, "EA_Template");
   uint rc = trade.ResultRetcode();
   if(!sent || !RetcodeOk(rc))
      PrintFormat("%s %.2f lots failed: %u %s", isBuy ? "Buy" : "Sell", lots, rc,
                  trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
//| Lots that lose InpRiskPercent of equity if the stop is hit        |
//+------------------------------------------------------------------+
double RiskLots(const double entry, const double sl)
  {
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   double step      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(tickSize <= 0.0 || tickValue <= 0.0 || step <= 0.0)
      return(0.0);

   double riskMoney   = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPercent / 100.0;
   double lossPerLot  = MathAbs(entry - sl) / tickSize * tickValue;
   if(lossPerLot <= 0.0)
      return(0.0);

   double lots = MathFloor(riskMoney / lossPerLot / step) * step;  // round DOWN
   lots = MathMin(lots, maxLot);
   if(lots < minLot)
      return(0.0);                  // never round up into more risk
   int digits = (int)MathMax(0, MathCeil(-MathLog10(step)));
   return(NormalizeDouble(lots, digits));
  }

//+------------------------------------------------------------------+
double NormalizePrice(const double price)
  {
   double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick <= 0.0)
      return(NormalizeDouble(price, _Digits));
   return(NormalizeDouble(MathRound(price / tick) * tick, _Digits));
  }

//+------------------------------------------------------------------+
bool RetcodeOk(const uint rc)
  {
   return(rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED ||
          rc == TRADE_RETCODE_DONE_PARTIAL);
  }

//+------------------------------------------------------------------+
//| Custom optimisation criterion: profit factor penalised by depth   |
//| of drawdown, and rejected below 30 trades.                        |
//+------------------------------------------------------------------+
double OnTester()
  {
   double trades = TesterStatistics(STAT_TRADES);
   double pf     = TesterStatistics(STAT_PROFIT_FACTOR);
   double ddPct  = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(trades < 30.0)
      return(0.0);
   return(pf * (1.0 - ddPct / 100.0));
  }
//+------------------------------------------------------------------+
