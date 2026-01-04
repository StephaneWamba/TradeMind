"""LLM decision logs endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.trade import Trade
from app.models.strategy import StrategyExecution

router = APIRouter()


@router.get("/logs")
async def get_llm_logs(
    strategy_id: int = Query(None, description="Filter by strategy ID"),
    limit: int = Query(100, description="Number of logs to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get LLM decision logs with reasoning and actions.
    
    Returns trades and strategy executions with LLM reasoning.
    """
    logs = []
    
    # Get trades with LLM reasoning
    stmt = select(Trade).where(Trade.llm_reasoning.isnot(None))
    if strategy_id:
        stmt = stmt.where(Trade.strategy_id == strategy_id)
    stmt = stmt.order_by(desc(Trade.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    trades = result.scalars().all()
    
    for trade in trades:
        logs.append({
            "id": trade.id,
            "type": "trade",
            "strategy_id": trade.strategy_id,
            "symbol": trade.symbol,
            "action": "BUY" if trade.status == "open" else "SELL",
            "reasoning": trade.llm_reasoning,
            "confidence": trade.llm_confidence,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "amount": trade.amount,
            "pnl": trade.pnl,
            "pnl_percent": trade.pnl_percent,
            "status": trade.status,
            "timestamp": trade.entry_time.isoformat() if trade.entry_time else trade.created_at.isoformat(),
        })
    
    # Get strategy executions with LLM reasoning
    stmt_exec = select(StrategyExecution).where(
        StrategyExecution.llm_reasoning.isnot(None)
    )
    if strategy_id:
        stmt_exec = stmt_exec.where(StrategyExecution.strategy_id == strategy_id)
    stmt_exec = stmt_exec.order_by(desc(StrategyExecution.created_at)).limit(limit)
    
    result_exec = await db.execute(stmt_exec)
    executions = result_exec.scalars().all()
    
    for exec in executions:
        result_data = exec.result or {}
        logs.append({
            "id": exec.id,
            "type": "execution",
            "strategy_id": exec.strategy_id,
            "execution_type": exec.execution_type,
            "reasoning": exec.llm_reasoning,
            "result": result_data,
            "execution_time_ms": exec.execution_time_ms,
            "timestamp": exec.created_at.isoformat(),
        })
    
    # Sort by timestamp descending
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "logs": logs[:limit],
        "total": len(logs),
    }


