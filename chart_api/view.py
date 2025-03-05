from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from chart_api.charts import async_create_chart

app = FastAPI()


@app.get("/chart/{trading_pair}/{timeframe}")
async def get_chart(trading_pair: str,timeframe: str):

    try:
        if timeframe is not None:
            chart_bytes = await async_create_chart(trading_pair, timeframe)
        else:
            chart_bytes = await async_create_chart(trading_pair)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {e}")

    return StreamingResponse(chart_bytes, media_type="image/png")
