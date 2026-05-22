#!/usr/bin/env python3
import os

import uvicorn

if __name__ == "__main__":
    reload = os.getenv("ENV", "development") != "production"
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=reload)
