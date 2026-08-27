import pytest
import anyio
from app.services.openapi_parser import OpenApiParser
@pytest.mark.anyio
async def test_openapi_parser():
    oas2_yaml = """
swagger: '2.0'
info:
  title: Petstore 2.0
  version: 1.0.0
host: petstore.swagger.io
basePath: /v2
schemes:
  - https
paths:
  /pet/{petId}:
    get:
      summary: Find pet by ID
      operationId: getPetById
      parameters:
        - name: petId
          in: path
          required: true
          type: integer
      responses:
        200:
          description: OK
"""
    res2 = await OpenApiParser.parse(oas2_yaml)
    assert res2["version"] == "swagger_2.0"
    assert res2["base_url"] == "https://petstore.swagger.io/v2"
    assert len(res2["endpoints"]) == 1
    assert res2["endpoints"][0]["name"] == "getpetbyid"
    assert "petId" in res2["endpoints"][0]["parameters_schema"]["properties"]
    print("OAS 2.0 測試通過: version =", res2["version"], ", endpoints =", len(res2["endpoints"]))
    oas3_yaml = """
openapi: 3.0.3
info:
  title: User API 3.0
  version: 1.0.0
servers:
  - url: https://api.example.com/v3
paths:
  /users:
    post:
      summary: Create new user
      operationId: createUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                username:
                  type: string
                email:
                  type: string
              required:
                - username
"""
    res3 = await OpenApiParser.parse(oas3_yaml)
    assert res3["version"] == "openapi_3.0"
    assert res3["base_url"] == "https://api.example.com/v3"
    assert len(res3["endpoints"]) == 1
    assert "username" in res3["endpoints"][0]["parameters_schema"]["properties"]
    print("OAS 3.0 測試通過: version =", res3["version"], ", properties =", list(res3["endpoints"][0]["parameters_schema"]["properties"].keys()))
    oas31_yaml = """
openapi: 3.1.0
info:
  title: Webhook API 3.1
  version: 2.0.0
servers:
  - url: https://api.v31.com
paths:
  /items/{itemId}:
    put:
      summary: Update Item
      operationId: updateItem
      parameters:
        - name: itemId
          in: path
          required: true
          schema:
            type:
              - string
              - integer
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                price:
                  type:
                    - number
                    - 'null'
"""
    res31 = await OpenApiParser.parse(oas31_yaml)
    assert res31["version"] == "openapi_3.1"
    assert res31["base_url"] == "https://api.v31.com"
    assert len(res31["endpoints"]) == 1
    print("OAS 3.1 測試通過: version =", res31["version"], ", endpoints =", len(res31["endpoints"]))
    print("All OpenAPI Parser tests passed successfully!")
if __name__ == "__main__":
    asyncio.run(main())