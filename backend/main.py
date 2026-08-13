from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "SMC Academy Referral API is running!"}