The `IndexesClient.IndexedAssetsClient` class provides methods to manage indexed assets within an index.

# Workflow

Before you begin, create an index if you don’t have one.

<Steps>
    <Step>
        [Upload your content](/v1.3/sdk-reference/python/upload-content) using direct or multipart uploads. The platform creates an asset and return its unique identifier.
    </Step>
    <Step>
        Index your content using the [`indexes.indexed_assets.create`](/v1.3/sdk-reference/python/index-content#index-an-asset) method.
    </Step>
    <Step>
        Monitor the indexing status until it shows ready using the [`indexes.indexed_assets.retrieve`](/v1.3/sdk-reference/python/index-content#retrieve-an-indexed-asset) method.
    </Step>
    <Step>
        [Search](/v1.3/sdk-reference/python/search) or [analyze](/v1.3/sdk-reference/python/analyze-videos) your content.
    </Step>
</Steps>


# Methods

## Index an asset

**Description**: This method indexes an uploaded asset to make it searchable and analyzable. Indexing processes your content and extracts information that enables the platform to search and analyze your videos.

This operation is asynchronous. The platform returns an indexed asset ID immediately and processes your content in the background. Monitor the indexing status to know when your content is ready to use.

Your asset must meet the requirements based on your workflow:
- **Search**: [Marengo requirements](/v1.3/docs/concepts/models/marengo#video-file-requirements)
- **Video analysis**: [Pegasus requirements](/v1.3/docs/concepts/models/pegasus#input-requirements)

If you want to both search and analyze your videos, the most restrictive requirements apply.

**Function signature and example**:

<CodeGroup>

```python Function signature
def create(
    self,
    index_id: str,
    *,
    asset_id: str,
    enable_video_stream: typing.Optional[bool] = OMIT,
    request_options: typing.Optional[RequestOptions] = None,
) -> IndexedAssetsCreateResponse
```

```python Python example
from twelvelabs import TwelveLabs

indexed_asset = client.indexes.indexed_assets.create(
    index_id="<YOUR_INDEX_ID>",
    asset_id="<YOUR_ASSET_ID>",
    enable_video_stream=True,
)

print(f"Indexed asset ID: {indexed_asset.id}")
print("Indexing started. Monitor status using the retrieve method.")
```

</CodeGroup>

**Parameters**:

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `index_id` | `str` | Yes | The unique identifier of the index to which the asset will be indexed. |
| `asset_id` | `str` | Yes | The unique identifier of the asset to index. |
| `enable_video_stream` | `bool` | No | This parameter indicates if the platform stores the video for streaming. When set to `true`, the platform stores the video, and you can retrieve its URL to access the stream over the HLS protocol. |
| `request_options` | `RequestOptions` | No | Request-specific configuration. |

**Return value**: Returns an `IndexedAssetsCreateResponse` object containing the unique identifier of the indexed asset.

The `IndexedAssetsCreateResponse` class contains the following properties:

| Name | Type | Description |
| ---- | ---- | ----------- |
| `id` | `Optional[str]` | The unique identifier of the indexed asset. Use it to monitor the indexing progress. |

**API Reference**: [Index an asset](/v1.3/api-reference/index-content/create)


## Retrieve an indexed asset

**Description**: This method retrieves information about an indexed asset, including its status, metadata, and optional embeddings or transcription.

Use this method to:

- Monitor the indexing progress:
    - Call this endpoint after creating an indexed asset
    - Check the `status` field until it shows `ready`
    - Once ready, your content is available for search and analysis

- Retrieve the asset metadata:
    - Retrieve system metadata (duration, resolution, filename)
    - Access user-defined metadata

- Retrieve the embeddings:
    - Include the `embeddingOption` parameter to retrieve video embeddings
    - Requires the Marengo video understanding model to be enabled in your index

- Retrieve transcriptions:
    - Set the transcription parameter to true to retrieve spoken words from your video
**Function signature and example**:

<CodeGroup>

```python Function signature
def retrieve(
    self,
    index_id: str,
    indexed_asset_id: str,
    *,
    embedding_option: typing.Optional[
        typing.Union[
            IndexedAssetsRetrieveRequestEmbeddingOptionItem,
            typing.Sequence[IndexedAssetsRetrieveRequestEmbeddingOptionItem],
        ]
    ] = None,
    transcription: typing.Optional[bool] = None,
    request_options: typing.Optional[RequestOptions] = None,
) -> IndexedAssetDetailed
```

```python Python example
from twelvelabs import TwelveLabs
import time

# Poll until indexing is complete
while True:
    asset = client.indexes.indexed_assets.retrieve(
        index_id="<YOUR_INDEX_ID>",
        indexed_asset_id="<YOUR_INDEXED_ASSET_ID>",
    )

    print(f"Status: {asset.status}")

    if asset.status == "ready":
        print("Indexing complete!")
        print(f"Duration: {asset.system_metadata.duration}s")
        print(f"Resolution: {asset.system_metadata.width}x{asset.system_metadata.height}")
        break
    elif asset.status == "failed":
        print("Indexing failed")
        break
    else:
        time.sleep(5)
```

{/* ```python Retrieve with transcription
from twelvelabs import TwelveLabs

asset = client.indexes.indexed_assets.retrieve(
    index_id="<INDEX_ID>",
    indexed_asset_id="<YOUR_INDEXED_ASSET_ID>",
    transcription=True,
)

print(f"Status: {asset.status}")
if asset.transcription:
    print("Transcription:")
    for segment in asset.transcription:
        print(f"  [{segment.start}s - {segment.end}s]: {segment.value}")
```

```python Retrieve embeddings
from twelvelabs import TwelveLabs

client = TwelveLabs(
    api_key="YOUR_API_KEY",
)

# Retrieve indexed asset with embeddings
asset = client.indexes.indexed_assets.retrieve(
    index_id="<YOUR_INDEX_ID>",
    indexed_asset_id="<YOUR_INDEXED_ASSET_ID>",
    embedding_option=["visual", "audio"],
)

print(f"Status: {asset.status}")
if asset.embedding:
    print(f"Video embeddings: {len(asset.embedding.video_embedding)} segments")
``` */}

</CodeGroup>

**Parameters**:

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `index_id` | `str` | Yes | The unique identifier of the index to which the indexed asset has been uploaded. |
| `indexed_asset_id` | `str` | Yes | The unique identifier of the indexed asset to retrieve. |
| `embedding_option` | `Union`<br/>`[IndexedAssetsRetrieveRequestEmbeddingOptionItem,`<br/>`Sequence`<br/>`[IndexedAssetsRetrieveRequestEmbeddingOptionItem]]` | No | Specifies which types of embeddings to retrieve. Values vary by model version:<br/>- **Marengo 3.0**: `visual`, `audio`, `transcription`<br/>- **Marengo 2.7**: `visual-text`, `audio`<br/><br/>To retrieve embeddings, the video must be indexed using the Marengo model.|
| `transcription` | `bool` | No | Indicates whether to retrieve a transcription of the spoken words for the indexed asset. |
| `request_options` | `RequestOptions` | No | Request-specific configuration. |

**Return value**: Returns an `IndexedAssetDetailed` object containing detailed information about the indexed asset.

The `IndexedAssetDetailed` class extends `IndexedAsset` and contains the following additional properties:

| Name | Type | Description |
| ---- | ---- | ----------- |
| `user_metadata` | `Optional[Dict[str, Optional[Any]]]` | User-generated metadata about the indexed asset. |
| `hls` | `Optional[HlsObject]` | The platform returns this object only for videos uploaded with the `enable_video_stream` parameter set to `true`. |
| `embedding` | `Optional[IndexedAssetDetailedEmbedding]` | Contains the embedding and the associated information. The platform returns this field when the `embedding_option` parameter is specified in the request. |
| `transcription` | `Optional[List[TranscriptionDataItem]]` | A list of transcription segments. The platform returns this field when the `transcription` parameter is set to `true`. |

The `IndexedAssetDetailed` class also inherits all properties from `IndexedAsset`:

| Name | Type | Description |
| ---- | ---- | ----------- |
| `id` | `Optional[str]` | The unique identifier of the indexed asset. |
| `created_at` | `Optional[str]` | The date and time, in RFC 3339 format, when the indexing task was created. |
| `updated_at` | `Optional[str]` | The date and time, in RFC 3339 format, when the indexing task was last updated. |
| `indexed_at` | `Optional[str]` | The date and time, in RFC 3339 format, when the indexing task was completed. |
| `status` | `Optional[IndexedAssetStatus]` | The status of the indexing task. Values: `ready`, `pending`, `queued`, `indexing`, `failed`. |
| `system_metadata` | `Optional[IndexedAssetSystemMetadata]` | System-generated metadata about the indexed asset. |

The `IndexedAssetSystemMetadata` class contains the following properties:

| Name | Type | Description |
| ---- | ---- | ----------- |
| `filename` | `Optional[str]` | The filename of the indexed asset. |
| `duration` | `Optional[float]` | The duration of the video in seconds. |
| `fps` | `Optional[float]` | The frames per second of the video. |
| `width` | `Optional[int]` | The width of the video in pixels. |
| `height` | `Optional[int]` | The height of the video in pixels. |
| `size` | `Optional[float]` | The size of the file in bytes. |

The `HlsObject` class contains the following properties:

| Name | Type | Description |
| ---- | ---- | ----------- |
| `video_url` | `Optional[str]` | The URL of the video. You can use this URL to access the stream over the HLS protocol. |
| `thumbnail_urls` | `Optional[List[str]]` | An array containing the URLs of thumbnails. |
| `status` | `Optional[HlsObjectStatus]` | The encoding status of the video file. Values: `PROCESSING` (video is being encoded), `COMPLETE` (encoding finished), `CANCELED` (encoding was canceled), `ERROR` (encoding error occurred). |
| `updated_at` | `Optional[str]` | The date and time, in RFC 3339 format, when the encoding status was last updated. |

The `TranscriptionDataItem` class contains the following properties:

| Name | Type | Description |
| ---- | ---- | ----------- |
| `start` | `Optional[float]` | The start of the time range, expressed in seconds. |
| `end` | `Optional[float]` | The end of the time range, expressed in seconds. |
| `value` | `Optional[str]` | Text representing the spoken words within this time range. |

**API Reference**: [Retrieve an indexed asset](/v1.3/api-reference/index-content/create)


## Update an indexed asset

**Description**: This method updates one or more fields of the metadata of an indexed asset. You can also delete a field by setting it to `null`.

**Function signature and example**:

<CodeGroup>

```python Function signature
def update(
    self,
    index_id: str,
    indexed_asset_id: str,
    *,
    user_metadata: typing.Optional[UserMetadata] = OMIT,
    request_options: typing.Optional[RequestOptions] = None,
) -> None
```

```python Python example
from twelvelabs import TwelveLabs

client.indexes.indexed_assets.update(
    index_id="<YOUR_INDEX_ID>",
    indexed_asset_id="<YOUR_INDEXED_ASSET_ID>",
    user_metadata={
        "category": "recentlyAdded",
        "batchNumber": 5,
        "rating": 9.3,
        "needsReview": True,
    },
)

print("Metadata updated successfully")
```

</CodeGroup>

**Parameters**:

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `index_id` | `str` | Yes | The unique identifier of the index to which the indexed asset has been uploaded. |
| `indexed_asset_id` | `str` | Yes | The unique identifier of the indexed asset to update. |
| `user_metadata` | `UserMetadata` | No | User-defined metadata to associate with the indexed asset. You can use strings, integers, floats, and booleans as values. |
| `request_options` | `RequestOptions` | No | Request-specific configuration. |

**Return value**: Returns `None`.

**API Reference**: [Update indexed asset](/v1.3/api-reference/index-content/update)

## List indexed assets

**Description**: This method returns a list of the indexed assets in the specified index. By default, the platform returns your indexed assets sorted by creation date, with the newest at the top of the list.

**Function signature and example**:

<CodeGroup>

```python Function signature
def list(
    self,
    index_id: str,
    *,
    page: typing.Optional[int] = None,
    page_limit: typing.Optional[int] = None,
    sort_by: typing.Optional[str] = None,
    sort_option: typing.Optional[str] = None,
    status: typing.Optional[
        typing.Union[IndexedAssetsListRequestStatusItem, typing.Sequence[IndexedAssetsListRequestStatusItem]]
    ] = None,
    filename: typing.Optional[str] = None,
    duration: typing.Optional[float] = None,
    fps: typing.Optional[float] = None,
    width: typing.Optional[float] = None,
    height: typing.Optional[int] = None,
    size: typing.Optional[float] = None,
    created_at: typing.Optional[str] = None,
    updated_at: typing.Optional[str] = None,
    user_metadata: typing.Optional[
        typing.Dict[str, typing.Optional[IndexedAssetsListRequestUserMetadataValue]]
    ] = None,
    request_options: typing.Optional[RequestOptions] = None,
) -> SyncPager[IndexedAsset]
```

```python Pythone example
from twelvelabs import TwelveLabs


response = client.indexes.indexed_assets.list(
    index_id="<YOUR_INDEX_ID>",
    page=1,
    page_limit=10,
)

print("Indexed assets:")
for asset in response:
    print(f"  ID: {asset.id}")
    print(f"  Status: {asset.status}")
    print(f"  Created: {asset.created_at}")
```
</CodeGroup>

**Parameters**:

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `index_id` | `str` | Yes | The unique identifier of the index for which the platform will retrieve the indexed assets. |
| `page` | `int` | No | A number that identifies the page to retrieve. Default: `1`. |
| `page_limit` | `int` | No | The number of items to return on each page. Default: `10`. Max: `50`. |
| `sort_by` | `str` | No | The field to sort on. Values: `updated_at`, `created_at`. Default: `created_at`. |
| `sort_option` | `str` | No | The sorting direction. Values: `asc`, `desc`. Default: `desc`. |
| `status` | `Union`<br/>`[IndexedAssetsListRequestStatusItem,`<br/>`Sequence`<br/>`[IndexedAssetsListRequestStatusItem]]` | No | Filter by one or more indexing task statuses. Values: `ready`, `pending`, `queued`, `indexing`, `failed`. |
| `filename` | `str` | No | Filter by filename. |
| `duration` | `float` | No | Filter by duration. Expressed in seconds. |
| `fps` | `float` | No | Filter by frames per second. |
| `width` | `float` | No | Filter by width. |
| `height` | `int` | No | Filter by height. |
| `size` | `float` | No | Filter by size. Expressed in bytes. |
| `created_at` | `str` | No | Filter indexed assets by the creation date and time of their associated indexing tasks, in the RFC 3339 format ("YYYY-MM-DDTHH:mm:ssZ"). |
| `updated_at` | `str` | No | Filter indexed assets by the last update date and time, in the RFC 3339 format ("YYYY-MM-DDTHH:mm:ssZ"). This filter applies only to indexed assets updated using the update method. |
| `user_metadata` | `Dict`<br/>`[str, `<br/>`Optional[IndexedAssetsListRequestUserMetadataValue]]` | No | Filter by custom user-defined metadata fields. To enable filtering, you must first add user-defined metadata to your video. |
| `request_options` | `RequestOptions` | No | Request-specific configuration. |

**Return value**: Returns a `SyncPager[IndexedAsset]` object that allows you to iterate through the paginated indexed asset results.

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

The `IndexedAsset` class contains the following properties:

| Name | Type | Description |
| ---- | ---- | ----------- |
| `id` | `Optional[str]` | A string representing the unique identifier of your indexed asset. |
| `created_at` | `Optional[str]` | A string indicating the date and time, in the RFC 3339 format ("YYYY-MM-DDTHH:mm:ssZ"), that the indexing task was created. |
| `updated_at` | `Optional[str]` | A string indicating the date and time, in the RFC 3339 format ("YYYY-MM-DDTHH:mm:ssZ"), that the indexing task was last updated. |
| `indexed_at` | `Optional[str]` | A string indicating the date and time, in the RFC 3339 format ("YYYY-MM-DDTHH:mm:ssZ"), that the indexing task has been completed. |
| `status` | `Optional[IndexedAssetStatus]` | The status of the indexing task. Values: `ready`, `pending`, `queued`, `indexing`, `failed`. |
| `system_metadata` | `Optional[IndexedAssetSystemMetadata]` | System-generated metadata about the indexed asset. |

**API Reference**: [List indexed assets](/v1.3/api-reference/index-content/list)


## Delete an indexed asset

**Description**: This method deletes all the information about the specified indexed asset. This action cannot be undone.

**Function signature and example**:

<CodeGroup>

```python Function signature
def delete(
    self,
    index_id: str,
    indexed_asset_id: str,
    *,
    request_options: typing.Optional[RequestOptions] = None
) -> None
```

```python Python example
from twelvelabs import TwelveLabs

client.indexes.indexed_assets.delete(
    index_id="<YOUR_INDEX_ID",
    indexed_asset_id="<YOUR_INDEXED_ASSET_ID>",
)

print("Indexed asset deleted successfully")
```

</CodeGroup>

**Parameters**:

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `index_id` | `str` | Yes | The unique identifier of the index to which the indexed asset has been uploaded. |
| `indexed_asset_id` | `str` | Yes | The unique identifier of the indexed asset to delete. |
| `request_options` | `RequestOptions` | No | Request-specific configuration. |

**Return value**: Returns `None`.

**API Reference**: [Delete an indexed asset](/v1.3/api-reference/index-content/delete)

