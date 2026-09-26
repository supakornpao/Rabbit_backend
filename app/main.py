import uvicorn
from fastapi import FastAPI,Query, UploadFile, Depends
from enum import Enum
from pydantic import BaseModel
from typing import Annotated

from io import BytesIO
from PIL import Image
import json
import urllib.request
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
from app.auth import models
from app.database import engine
from app.auth.router import router,get_current_user
from app.rabbits.router import router as rabbit_router
import os
from dotenv import load_dotenv
# Load variables from .env file
load_dotenv()
# Securely fetch them from the environment!
url = os.getenv("AZURE_ML_ENDPOINT_URL")
API_key = os.getenv("AZURE_ML_API_KEY")
if not API_key:
    raise Exception("Azure API Key not found in .env file!")

models.Base.metadata.create_all(bind=engine)

class Item(BaseModel):
    name:str
    description: str|None = None
    price : float
    tax : float | None = None


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows your Expo tunnel to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)
app.include_router(rabbit_router)

fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]

@app.post("/items/")
async def create_item(item:Item):
    item_dict = item.model_dump()
    if item.tax is not None:
        price_with_tax = item.price + item.tax
        item_dict.update({"price_with_tax": price_with_tax})
    return item_dict

@app.post("/items/{item_id}")
async def update_item(item_id:int, item:Item, q:str|None=None):
    result = {"item_id": item_id,**item.model_dump()}
    if q:
        result.update({"q":q})
    return result


@app.get("/items/")
async def read_item(q: Annotated[str | None, Query(min_length=3)]=None):
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile, current_user: models.User = Depends(get_current_user)):
    return {"filename": file.filename}

@app.post("/predict/")
async def prediction(file: UploadFile, current_user: models.User = Depends(get_current_user)):
    contents = await file.read()
    img = Image.open(BytesIO(contents)).convert('RGB')
    img_array = np.array(img).astype('uint8')
    input_data = img_array.tolist()
    sample_data = {"data":input_data}
    body = str.encode(json.dumps(sample_data))

    if not API_key:
        raise Exception("A key should be provided to invoke the endpoint")
    headers = {'Content-Type':'application/json', 'Accept': 'application/json', 'Authorization':('Bearer '+ API_key)}
    req = urllib.request.Request(url, body, headers)
    try:
        response = urllib.request.urlopen(req)
        result = response.read()
        
        azure_data = json.loads(json.loads(result)) 
        
        # 2. azure_data is now: {"result": "Melanoma: 99%"}
        result_string = azure_data.get("result", "")
        
        # 3. Split it into label and confidence
        if ":" in result_string:
            parts = result_string.split(":")
            label = parts[0].strip()
            confidence = parts[1].replace("%", "").strip()
            
            # 4. Return it nicely separated to React Native!
            return {
                "label": label,
                "confidence": float(confidence)
            }
            
        return azure_data

    except urllib.error.HTTPError as error:
        print("The request failed with status code: " + str(error.code))

        # Print the headers - they include the requert ID and the timestamp, which are useful for debugging the failure
        print(error.info())
        print(error.read().decode("utf8", 'ignore'))
        return error.read().decode("utf8",'ignore')




@app.get("/")
def greeting():
    return {"message": "Hello World"}

#uvicorn app.main:app --host 0.0.0.0 --reload

