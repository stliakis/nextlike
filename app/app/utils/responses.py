from fastapi.encoders import jsonable_encoder
from starlette import status
from starlette.responses import JSONResponse


def get_invalid_data_error(errors):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"errors": errors}),
    )
