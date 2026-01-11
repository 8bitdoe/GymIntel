The `AssetsClient` class provides methods to upload your media files to the platform. This method creates an asset that you can use in different workflows.


# Workflow

<Steps>
    <Step>
        Upload your file using the [`assets.create`](/v1.3/sdk-reference/python/upload-content/direct-uploads#create-an-asset) method. You receive the asset ID in the response.
    </Step>
    <Step>
        Monitor the indexing status using the [`assets.retrieve`](/v1.3/sdk-reference/python/upload-content/direct-uploads#retrieve-an-asset) method until it's ready.
    </Step>
    <Step>
        What you do next depends on your use case:
        - **For creating embeddings (videos, audio, images)**: Use the asset ID with the [Embed API v2](/v1.3/sdk-reference/python/create-embeddings-v-2).
        - **For entity search (images)**: Use the asset ID to [create entities](/v1.3/sdk-reference/python/manage-entities#create-an-entity).
        - **For search and analysis (videos)**: [Index your asset](/v1.3/sdk-reference/python/index-content#index-an-asset) using the asset ID.
    </Step>
</Steps>

# Methods

## Create an asset

**Description**: This method creates an asset by uploading a file to the platform. Assets are media files that you can use in downstream workflows, including indexing, analyzing video content, and creating entities.

**Supported content**: Video, audio, and images.

**Upload methods**:
- **Local file**: Set the `method` parameter to `direct` and use the `file` parameter to specify the file.
- **Publicly accessible URL**: Set the `method` parameter to `url` and use the `url` parameter to specify the URL of your file.

**File size**: 200MB maximum for local file uploads, 4GB maximum for URL uploads.

**Additional requirements** depend on your workflow:
- **Search**: [Marengo requirements](/v1.3/docs/concepts/models/marengo#video-file-requirements)
- **Video analysis**: [Pegasus requirements](/v1.3/docs/concepts/models/pegasus#input-requirements)
- **Entity search**: [Marengo image requirements](/v1.3/docs/concepts/models/marengo#image-file-requirements)
- **Create embeddings**: [Marengo requirements](/v1.3/docs/concepts/models/marengo#input-requirements)

**Function signature and example**:

<CodeGroup>

```python Function signature
def create(
    self,
    *,
    method: AssetsCreateRequestMethod,
    file: typing.Optional[core.File] = OMIT,
    url: typing.Optional[str] = OMIT,
    filename: typing.Optional[str] = OMIT,
    request_options: typing.Optional[RequestOptions] = None,
) -> Asset
```

```python Python example
from twelvelabs import TwelveLabs

asset = client.assets.create(
    method="url",
    url="<YOUR_VIDEO_URL>",
    filename="<YOUR_VIDEO_FILENAME>"
)

print(f"Asset ID: {asset.id}")
print(f"Status: {asset.status}")
print(f"Filename: {asset.filename}")
```

</CodeGroup>


**Parameters**:

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `method` | `AssetsCreateRequestMethod` | Yes | Specifies the upload method for the asset. Use `direct` to upload a local file or `url` for a publicly accessible URL. |
| `file` | `core.File` | No | The local file to upload. This parameter is required when `method` is set to `direct`. |
| `url` | `str` | No | The publicly accessible URL of a media file to upload. This parameter is required when `method` is set to `url`.<br/><br/>URL uploads have a maximum limit of 4GB. |
| `filename` | `str` | No | The optional filename of the asset. If not provided, the platform determines the filename from the file or URL. |
| `request_options` | `RequestOptions` | No | Request-specific configuration. |


**Return value**: Returns an object of type `Asset` representing the created asset.

The `Asset` class contains the following properties:

| Name | Type | Description |
| ---- | ---- | ----------- |
| `id` | `Optional[str]` | The unique identifier of the asset. |
| `method` | `Optional[AssetMethod]` | Indicates how you uploaded the asset. Values: `direct` (uploaded from your local file system), `url` (uploaded from a publicly accessible URL). |
| `status` | `Optional[AssetStatus]` | Indicates the current status of the asset. Values: `waiting` (the platform is preparing to process the upload), `processing` (the platform is processing the uploaded file), `ready` (the asset is ready to use). |
| `filename` | `Optional[str]` | The name of the file used to create the asset. |
| `file_type` | `Optional[str]` | The MIME type of the asset file. |
| `url` | `Optional[str]` | The URL to access your asset. Use this URL to preview or download the asset.<br/><br/>This URL expires after the time specified in the `url_expires_at` field. After expiration, you must retrieve the asset again to obtain a new URL. |
| `url_expires_at` | `Optional[datetime]` | The date and time, in RFC 3339 format ("YYYY-MM-DDTHH:mm:ssZ"), when the URL expires. After this time, the URL in the `url` field becomes invalid. Retrieve the asset again to obtain a new URL. |
| `created_at` | `Optional[datetime]` | The date and time, in RFC 3339 format ("YYYY-MM-DDTHH:mm:ssZ"), when the asset was created. |

**API Reference**: [Create an asset](/v1.3/api-reference/upload-content/direct-uploads/create)


## List assets

**Description**: This method returns a list of assets in your account.

The platform returns your assets sorted by creation date, with the newest at the top of the list.

**Function signature and example**:

<CodeGroup>

```python Function signature
def list(
    self,
    *,
    page: typing.Optional[int] = None,
    page_limit: typing.Optional[int] = None,
    asset_ids: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
    asset_types: typing.Optional[
        typing.Union[AssetsListRequestAssetTypesItem, typing.Sequence[AssetsListRequestAssetTypesItem]]
    ] = None,
    request_options: typing.Optional[RequestOptions] = None,
) -> SyncPager[Asset]
```

```python Python example
from twelvelabs import TwelveLabs

response = client.assets.list(
    page=1,
    page_limit=10,
)

print("Assets:")
for asset in response:
    print(f"  ID: {asset.id}")
    print(f"  Filename: {asset.filename}")
    print(f"  Status: {asset.status}")
    print(f"  Created: {asset.created_at}")
```

</CodeGroup>


**Parameters**:

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `page` | `int` | No | A number that identifies the page to retrieve. Default: `1`. |
| `page_limit` | `int` | No | The number of items to return on each page. Default: `10`. Max: `50`. |
| `asset_ids` | `Union[str, Sequence[str]]` | No | Filters the response to include only assets with the specified IDs. Provide one or more asset IDs. When you specify multiple IDs, the platform returns all matching assets. |
| `asset_types` | `Union`<br/>`[AssetsListRequestAssetTypesItem, Sequence[AssetsListRequestAssetTypesItem]]` | No | Filters the response to include only assets of the specified types. Provide one or more asset types. When you specify multiple types, the platform returns all matching assets. Values: `image`, `video`, `audio`. |
| `request_options` | `RequestOptions` | No | Request-specific configuration. |


**Return value**: Returns a `SyncPager[Asset]` object containing a paginated list of `Asset` objects, representing the assets that match the specified criteria. For details about the  `Asset` class see the [Create an asset](/v1.3/sdk-reference/python/upload-content/direct-uploads#create-an-asset) section above.

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

**API Reference**: [List assets](/v1.3/api-reference/upload-content/direct-uploads/list)


## Retrieve an asset

**Description**: This method retrieves details about the specified asset.

**Function signature and example**:

<CodeGroup>

```python Function signature
def retrieve(
    self,
    asset_id: str,
    *,
    request_options: typing.Optional[RequestOptions] = None
) -> Asset
```

```python Python example
from twelvelabs import TwelveLabs

asset = client.assets.retrieve(
    asset_id="<YOUR_ASSET_ID>",
)

print(f"Asset ID: {asset.id}")
print(f"Filename: {asset.filename}")
print(f"Status: {asset.status}")
print(f"File type: {asset.file_type}")
print(f"Method: {asset.method}")
print(f"URL: {asset.url}")
print(f"URL expires at: {asset.url_expires_at}")
print(f"Created at: {asset.created_at}")
```
</CodeGroup>

**Parameters**:

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `asset_id` | `str` | Yes | The unique identifier of the asset to retrieve. |
| `request_options` | `RequestOptions` | No | Request-specific configuration. |

**Return value**: Returns an `Asset` object containing details about the specified asset. For details about the `Asset` class, see the [Create an asset](/v1.3/sdk-reference/python/upload-content/direct-uploads#create-an-asset) section above.

**API Reference**: [Retrieve an asset](/v1.3/api-reference/upload-content/direct-uploads/retrieve)

## Delete an asset

**Description**: This method deletes the specified asset. This action cannot be undone.

**Function signature and example**:

<CodeGroup>

```python Function signature
def delete(
    self,
    asset_id: str,
    *,
    request_options: typing.Optional[RequestOptions] = None
) -> None
```

```python Python example
from twelvelabs import TwelveLabs

client.assets.delete(
    asset_id="<YOUR_ASSET_ID>",
)
```

</CodeGroup>

**Parameters**:

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `asset_id` | `str` | Yes | The unique identifier of the asset to delete. |
| `request_options` | `RequestOptions` | No | Request-specific configuration. |

**Return value**: Returns `None`.

**API Reference**: [Delete asset](/v1.3/api-reference/upload-content/direct-uploads/delete)

