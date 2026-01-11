An index is a basic unit for organizing and storing video data consisting of video embeddings and metadata. Indexes facilitate information retrieval and processing. The `IndexesClient` class provides methods to manage your indexes.

# Properties

| Name    | Type                                                                                                            | Description                                                    |
| :------ | :-------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------- |
| `videos` | `VideosClient` | Use this property to manage the videos uploaded to this index. |

# Methods

## Create an index

**Description**: This method creates a new index based on the provided parameters.

**Function signature and example**:

<CodeGroup>

```python Function signature
def create(
    self,
    *,
    index_name: str,
    models: typing.Sequence[IndexesCreateRequestModelsItem],
    addons: typing.Optional[typing.Sequence[str]] = OMIT,
    request_options: typing.Optional[RequestOptions] = None,
) -> IndexesCreateResponse:
```

```python Python example
from twelvelabs import TwelveLabs
from twelvelabs.indexes import IndexesCreateRequestModelsItem

index = client.indexes.create(
    index_name="<YOUR_INDEX_NAME>",
    models=[
        IndexesCreateRequestModelsItem(
            model_name="marengo3.0", model_options=["visual", "audio"]
        )
    ]
)
print(f"ID: {index.id}")
```
</CodeGroup>

**Parameters**

| Name       | Type                     | Required | Description                                                                                                                                                                                                                                                                                      |
| :--------- | :----------------------- | :------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `index_name` | `str` | Yes | The name of the new index. Use a succinct and descriptive name.|
| `models` | `typing.`<br/>`Sequence`<br/>`[IndexesCreateRequestModelsItem]`| Yes | An array of objects specifying the video understanding models and the model options you want to enable for this index. Each object is a dictionary with two keys: `model_name` and `model_options`. |
| `addons`        | `typing.`<br/>`Optional`<br/>`[typing.`<br/>`Sequence[str]]`       | No       | An array of add-ons to enable, such as `"thumbnail"`. If omitted, no add-ons are enabled.      |
| `request_options` | `typing.`<br/>`Optional`<br/>`[RequestOptions]`           | No       | Request-specific configuration.                                                       |

The `IndexesCreateRequestModelsItem` class defines the model configuration for your index:

**Properties**

| Name | Type | Required | Description |
| :--- | :--- | :------- | :---------- |
| `model_name` | `str` | Yes | The name of the model to enable. The following models are available:<br/>- `marengo3.0`:  Enhanced model with sports intelligence and extended content support. For a list of the new features, see the [New in Marengo 3.0](/v1.3/docs/concepts/models/marengo#new-in-marengo-30) section.<br/>- `marengo2.7`: Video embedding model for multimodal search.<br/>- `pegasus1.2`: A model that analyzes multiple modalities to generate contextually relevant text based on the content of your videos. |
| `model_options` | `List[str]` | Yes | Specifies which modalities the platform analyzes. Values: `audio`, `visual`. For more details, see the [model options](/v1.3/docs/concepts/modalities#model-options) section. |

<Note title="Note">
    You cannot change the model configuration after creating the index.
</Note>


**Return value**: Returns an `IndexesCreateResponse` object containing the unique identifier of the newly created index.

**API Reference**: [Create an index](/v1.3/api-reference/indexes/create).

**Related guide**: [Indexes](/v1.3/docs/concepts/indexes).

## Retrieve an index

**Description**: This method retrieves details of a specific index.

**Function signature and example**:

<CodeGroup>

```python Function signature
def retrieve(self, index_id: str, *, request_options: typing.Optional[RequestOptions] = None) -> IndexSchema
```

```Python Python example
from twelvelabs import TwelveLabs

retrieved_index = client.indexes.retrieve(index_id="<YOUR_INDEX_ID")
print(f"ID: {retrieved_index.id}")
print(f"Name: {retrieved_index.index_name}")
if retrieved_index.models is not None:
  print("Models:")
  for i, model in enumerate(retrieved_index.models, 1):
      print(f"  Model {i}:")
      print(f"    Name: {model.model_name}")
      print(f"    Options: {model.model_options}")
print(f"Video count: {retrieved_index.video_count}")
print(f"Total duration: {retrieved_index.total_duration} seconds")
print(f"Created at: {retrieved_index.created_at}")
if retrieved_index.updated_at:
    print(f"Updated at: {retrieved_index.updated_at}")
if retrieved_index.expires_at:
    print(f"Expires at: {retrieved_index.expires_at}")
if retrieved_index.addons:
    print(f"Add-ons: {retrieved_index.addons}")
```
</CodeGroup>

**Parameters**

| Name       | Type   | Required | Description                                           |
| :--------- | :----- | :------- | :---------------------------------------------------- |
| `index_id`       | `str`  | Yes      | The unique identifier of the index to retrieve.       |
| `request_options` | `typing.Optional[RequestOptions]` | No       | Request-specific configuration. |

**Return value**: Returns an `IndexSchema` object representing the retrieved index.

The `IndexSchema` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `id` | `Optional[str]` | The unique identifier of the index. It is assigned by the platform when an index is created. |
| `created_at` | `Optional[str]` | The date and time, in the RFC 3339 format, that the index was created. |
| `updated_at` | `Optional[str]` | The date and time, in the RFC 3339 format, that the index has been updated. |
| `expires_at` | `Optional[str]` | The date and time, in the RFC 3339 format, when your index will expire. If you're on the Free plan, the platform retains your index data for 90 days from creation. If you're on the Developer plan, this field is set to `null`, indicating no expiration. |
| `index_name` | `Optional[str]` | The name of the index. |
| `total_duration` | `Optional[float]` | The total duration, in seconds, of the videos in the index. |
| `video_count` | `Optional[float]` | The number of videos uploaded to this index. |
| `models` | `Optional[List[IndexModelsItem]]` | An array containing the list of the video understanding models enabled for this index. |
| `addons` | `Optional[List[str]]` | The list of the add-ons that are enabled for this index. |

The `IndexModelsItem` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `model_name` | `Optional[str]` | The name of the model. |
| `model_options` | `Optional[List[str]]` | An array of strings that contains the model options enabled for this index. |


**API Reference**: [Retrieve an index](/v1.3/api-reference/indexes/retrieve).

## List indexes

**Description**: This method retrieves a paginated list of indexes based on the provided parameters. By default, the platform returns your indexes sorted by creation date, with the newest at the top of the list.

**Function signature and example**:

<CodeGroup>

```python Function signature
def list(
    self,
    *,
    page: typing.Optional[int] = None,
    page_limit: typing.Optional[int] = None,
    sort_by: typing.Optional[str] = None,
    sort_option: typing.Optional[str] = None,
    index_name: typing.Optional[str] = None,
    model_options: typing.Optional[str] = None,
    model_family: typing.Optional[str] = None,
    created_at: typing.Optional[str] = None,
    updated_at: typing.Optional[str] = None,
    request_options: typing.Optional[RequestOptions] = None,
) -> SyncPager[IndexSchema]
```
```python Python example
from twelvelabs import TwelveLabs

indexes = client.indexes.list(
    index_name="<YOUR_INDEX_NAME>",
    page=1,
    page_limit=5,
    model_options="visual,audio",
    model_family="marengo",
    sort_by="updated_at",
    sort_option="asc",
    created_at="2024-08-16T16:53:59Z",
    updated_at="2024-08-16T16:55:59Z",
)
for index in indexes:
    print(f"ID: {index.id}")
    print(f"  Name: {index.index_name}")
    print("  Models:")
    for i, model in enumerate(index.models or [], 1):
        print(f"    Model {i}:")
        print(f"      Name: {model.model_name}")
        print(f"      Options: {model.model_options}")
    print(f"  Video count: {index.video_count}")
    print(f"  Total duration: {index.total_duration} seconds")
    print(f"  Created at: {index.created_at}")
    if index.updated_at:
        print(f"  Updated at: {index.updated_at}")
```
</CodeGroup>

**Parameters**

| Name              | Type                              | Required | Description                                                                                   |
|-------------------|-----------------------------------|----------|-----------------------------------------------------------------------------------------------|
| `page`            | `typing.`<br/>`Optional[int]`            | No       | The page number to retrieve. Default: 1.                                                    |
| `page_limit`      | `typing.`<br/>`Optional[int]`            | No       | The number of items per page. Default: 10. Max: 50.                                   |
| `sort_by`         | `typing.`<br/>`Optional[str]`            | No       | The field to sort on. The following options are available: "updated_at" - Sorts by the time when the item was updated, "created_at" - Sorts by the time when the item was created. Default: "created_at".            |
| `sort_option`     | `typing.`<br/>`Optional[str]`            | No       | The sorting direction. The following options are available: "asc", "desc". Default: "desc".                                      |
| `index_name`      | `typing.`<br/>`Optional[str]`            | No       | Filter by the name of an index.                                                               |
| `model_options`   | `typing.`<br/>`Optional[str]`            | No       | Filter by the model options. When filtering by multiple model options, the values must be comma-separated. Example: `"visual,audio"`).                            |
| `model_family`    | `typing.`<br/>`Optional[str]`            | No       | Filter by the model family. This parameter can take one of the following values: "marengo" or "pegasus". You can specify a single value.                                           |
| `created_at`      | `typing.`<br/>`Optional[str]`            | No       |  Filter indexes by the creation date and time, in the RFC 3339 format ("YYYY-MM-DDTHH:mm:ssZ"). The platform returns the indexes that were created on the specified date at or after the given time.           |
| `updated_at`      | `typing.`<br/>`Optional[str]`            | No       | Filter indexes by the last update date and time, in the RFC 3339 format ("YYYY-MM-DDTHH:mm:ssZ"). The platform returns the indexes that were last updated on the specified date at or after the given time.        |
| `request_options` | `typing.`<br/>`Optional[RequestOptions]` | No       | Request-specific configuration.                                                       |


**Return value**: Returns a `SyncPager[IndexSchema]` object containing a paginated list of `IndexSchema` objects, representing the indexes that match the specified criteria. See the [Retrieve an index](#retrieve-an-index) section above for complete property details.

The `SyncPager[T]` class contains the following properties and methods:

| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `items` | `Optional[List[T]]` | A list containing the current page of items. Can be `None`. |
| `has_next` | `bool` | Indicates whether there is a next page to load. |
| `get_next` | `Optional[Callable[[], Optional[SyncPager[T]]]]` | A callable function that retrieves the next page. Can be `None`. |
| `response` | `Optional[BaseHttpResponse]` | The HTTP response object. Can be `None`. |
| `next_page()` | `Optional[SyncPager[T]]` | Calls `get_next()` if available and returns the next page object. |
| `__iter__()` | `Iterator[T]` | Allows iteration through all items across all pages using `for` loops. |
| `iter_pages()` | `Iterator[SyncPager[T]]` | Allows iteration through page objects themselves. |

**API Reference**: [List indexes](/v1.3/api-reference/indexes/list).

## Update an index

**Description**: This method updates the name of an existing index.

**Function signature and example**:

<CodeGroup>

```python Function signature
def update(
    self, index_id: str, *, index_name: str, request_options: typing.Optional[RequestOptions] = None
) -> None
```
```python Python example
from twelvelabs import TwelveLabs

client.indexes.update(index_id="<INDEX_ID>", index_name="<NEW_INDEX_NAME>")
```
</CodeGroup>

**Parameters**:

| Name              | Type                              | Required | Description                                           |
|-------------------|-----------------------------------|----------|-------------------------------------------------------|
| `index_id`        | `str`                             | Yes      | The unique identifier of the index to update.         |
| `index_name`      | `str`                             | Yes      | The new name of the index.                            |
| `request_options` | `typing.`<br/>`Optional[RequestOptions]` | No       | Request-specific configuration.              |

**Return Value**: `None`. This method doesn't return any data upon successful completion.

**API Reference**: [Update an index](/v1.3/api-reference/indexes/update).

## Delete an index

**Description**: This method deletes an existing index.

**Function signature and example**:

<CodeGroup>

```python Function signature
def delete(self, index_id: str, *, request_options: typing.Optional[RequestOptions] = None) -> None
```
```python Python  example
from twelvelabs import TwelveLabs

client.indexes.delete(index_id="<YOUR_INDEX_ID>")
```
</CodeGroup>

**Parameters**:

| Name       | Type     | Required | Description                                   |
| :--------- | :------- | :------- | :-------------------------------------------- |
| `index_id`       | `string` | Yes      | The unique identifier of the index to delete. |
| `request_options` | `typing.`<br/>`Optional[RequestOptions]` | No       | Request-specific configuration.              |

**Return value**:  `None`. This method doesn't return any data upon successful completion.

**API Reference**: [Delete an index](/v1.3/api-reference/indexes/delete)


# Error codes

This section lists the most common error messages you may encounter while managing indexes.

- `index_option_cannot_be_changed`
  - Index option cannot be changed. Please remove index_options parameter and try again. If you want to change index option, please create new index.
- `index_engine_cannot_be_changed`
  - Index engine cannot be changed. Please remove engine_id parameter and try again. If you want to change engine, please create new index.
- `index_name_already_exists`
  - Index name `{index_name}` already exists. Please use another unique name and try again.
