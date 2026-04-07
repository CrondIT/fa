from enum import Enum
from fastapi import FastAPI, Path, Query
from pydantic import BaseModel
from typing import Annotated


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None


class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[
        int,
        Path(title="The ID of the item to get", ge=1, le=100)
        ],
    q: Annotated[str | None, Query(alias="item-query")] = None,
):
    results = {"item_id": item_id}
    if q:
        results.update({"q": q})
    return results


@app.post("/items/")
async def create_item(item: Item):
    return item


@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    if model_name is ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}

    if model_name.value == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}

    return {"model_name": model_name, "message": "Have some residuals"}
