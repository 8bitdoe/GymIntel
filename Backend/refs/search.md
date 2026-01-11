The `SearchClient` class provides methods to perform search requests.

[**Related quickstart notebook**](https://colab.research.google.com/github/twelvelabs-io/twelvelabs-developer-experience/blob/main/quickstarts/TwelveLabs_Quickstart_Search.ipynb)

# Methods

## Make a search request

**Description**: This method performs a search across a specific index using text, media, or a combination of both as your query and returns a paginated iterator of search results.

Text queries:
- Use the `query_text` parameter to specify your query.

Media queries:
- Set the `query_media_type` parameter to the corresponding media type (example: `image`).
- Specify either one of the following parameters:
    - `query_media_url`: Publicly accessible URL of your media file.
    - `query_media_file`: Local media file.
    If both `query_media_url` and `query_media_file` are specified in the same request, `query_media_url` takes precedence.

Composed text and media queries (Marengo 3.0 only):
- Use the `query_text` parameter for your text query.
- Set `query_media_type` to `image`.
- Specify the image using either the `query_media_url` or the `query_media_file` parameter.

<Note title="Note">
    When using images in your search queries (either as media queries or in composed searches), ensure your image files meet the [requirements](/v1.3/docs/concepts/models/marengo#image-file-requirements).
</Note>

Entity search (Marengo 3.0 only):
    
- To find a specific person in your videos, enclose the unique identifier of the entity you want to find in the `query_text` parameter.
{/* - You must include a minimum of five assets in an entity before it can be utilized in a search request. */}

For instructions on setting up and using this feature, see the [Entity search](/v1.3/docs/guides/search/entity-search) page.

**Function signature and example**:

<CodeGroup>

```python Function signature
def query(
    self,
    *,
    index_id: str,
    search_options: typing.List[SearchCreateRequestSearchOptionsItem],
    query_media_type: typing.Optional[typing.Literal["image"]] = OMIT,
    query_media_url: typing.Optional[str] = OMIT,
    query_media_file: typing.Optional[core.File] = OMIT,
    query_text: typing.Optional[str] = OMIT,
    group_by: typing.Optional[SearchCreateRequestGroupBy] = OMIT,
    sort_option: typing.Optional[SearchCreateRequestSortOption] = OMIT,
    operator: typing.Optional[SearchCreateRequestOperator] = OMIT,
    page_limit: typing.Optional[int] = OMIT,
    filter: typing.Optional[str] = OMIT,
    request_options: typing.Optional[RequestOptions] = None,
) -> SyncPager[SearchItem]
```

```python Python example
from twelvelabs import TwelveLabs

response = client.search.query(
    index_id="<YOUR_INDEX_ID>",
    search_options=["visual", "audio"],
    query_text="<YOUR_QUERY>",
    group_by="video",
    operator="or",
    filter='{"category": "nature"}',
    page_limit=5,
    sort_option="score"
)

print("Search Results:")
for item in response:
    if item.id and item.clips:  # Grouped by video
        print(f"Video ID: {item.id}")
        for clip in item.clips:
            print("  Clip:")
            print(f"    Start: {clip.start}")
            print(f"    End: {clip.end}")
            print(f"    Video ID: {clip.video_id}")
            print(f"    Rank: {clip.rank}")
            print(f"    Thumbnail URL: {clip.thumbnail_url}")
    else:  # Individual clips
        print(f"  Start: {item.start}")
        print(f"  End: {item.end}")
        print(f"  Video ID: {item.video_id}")
        print(f"  Rank: {item.rank}")
        print(f"  Thumbnail URL: {item.thumbnail_url}")
        if item.transcription:
            print(f"  Transcription: {item.transcription}")
```
</CodeGroup>

**Parameters**:

{/* If you're using the Entity Search feature to search for specific persons in your video content,  you must enclose the unique identifier of your entity between the `<@` and `>` markers. For example, to search for an entity with the ID `entity123`, use `<@entity123> is walking` as your query. The maximum query length varies by model. */}

| Name                      | Type                                                 | Required | Description                                                                                                                                                    |
| ------------------------- | ---------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `index_id`                | `str`                                                | Yes      | The unique identifier of the index to search. |
| `search_options`          | `List`<br/>`[SearchCreateRequestSearchOptionsItem]`        | Yes      | Specifies the modalities the video understanding model uses to find relevant information.<br/>Available options:<br/>- `visual`: Searches visual content.<br/>- `audio`: Searches non-speech audio (Marengo 3.0) or all audio (Marengo 2.7).<br/>- `transcription`: Spoken words (Marengo 3.0 only)<br/>You can specify multiple search options in conjunction with the `operator` parameter to broaden or narrow your search.<br/>For detailed guidance and version-specific behavior, see the [Search options](/v1.3/docs/concepts/modalities#search-options) section. |
| `transcription_options` | `typing.Optional`<br/>`[typing.List`<br/>`[SearchCreateRequestTranscriptionOptionsItem]]` | No | Specifies how the platform matches your text query with the words spoken in the video. This parameter applies only when using Marengo 3.0 with the `search_options` parameter containing the `transcription` value.<br/>Available options:<br/>- `lexical`: Exact word matching<br/>- `semantic`: Meaning-based matching<br/>For details on when to use each option, see the [Transcription options](/v1.3/docs/concepts/modalities#transcription-options) section.<br/>**Default**: `["lexical", "semantic"]`. |
| `query_text`              | `str`                                                | No       | The text query to search for. This parameter is required for text queries. Marengo 3.0 supports up to 500 tokens per query, while Marengo 2.7 supports up to 77 tokens per query.                                                                                      |
| `query_media_type`        | `Literal["image"]`                                   | No       | The type of media you wish to use. This parameter is required for media queries. For example, to perform an image-based search, set this parameter to `image`. |
| `query_media_file`        | `core.File`                                          | No       | The media file to use as a query. This parameter is required for media queries if `query_media_url` is not provided.                                          |
| `query_media_url`         | `str`                                                | No       | The publicly accessible URL of a media file to use as a query. This parameter is required for media queries if `query_media_file` is not provided.             |
| `adjust_confidence_level` | `float`                                              | No       | The strictness of the thresholds for assigning the high, medium, or low confidence levels to search results. This parameter is deprecated in Marengo 3.0 and newer versions. Use the `rank` field in the response instead, which indicates the relevance ranking assigned by the model. Min: 0, Max: 1, Default: 0.5.                   |
| `group_by`                | `SearchCreateRequestGroupBy`                        | No       | Use this parameter to group or ungroup items in a response. Values: `video`, `clip`. Default: `clip`.                                                        |
| `threshold`               | `ThresholdSearch`                                    | No       | Filter on the level of confidence that the results match your query. This parameter is deprecated in Marengo 3.0 and newer versions. Use the `rank` field in the response instead, which indicates the relevance ranking assigned by the model. Values: `high`, `medium`, `low`, `none`.                                                 |
| `sort_option`             | `SearchCreateRequestSortOption`                     | No       | The sort order for the response. Values:<br/>- `score`: Sorts results by relevance ranking in ascending order (1 = most relevant). When `group_by` is `video`, sorts videos by highest relevance ranking (lowest number) among their clips<br/>- `clip_count`: Sorts videos by the number of matching clips in descending order. Clips within each video are sorted by relevance ranking in ascending order. Only available when `group_by` is set to `video`.<br/><br/> Default: `score`.                                                                            |
| `operator`                | `SearchCreateRequestOperator`                       | No       | Logical operator for combining search options. Values: `or`, `and`. Default: `or`.                                                                            |
| `page_limit`              | `int`                                                | No       | The number of items to return on each page. Max: 50.                                                                                                          |
| `filter`                  | `str`                                                | No       | A stringified object to filter search results based on video metadata or custom fields.                                                                       |
| `include_user_metadata` | `bool` | No | Specifies whether to include user-defined metadata in the search results. |
| `request_options`         | `RequestOptions`                                     | No       | Request-specific configuration.                                                                                                                                |


**Return value**: Returns a `SyncPager[SearchItem]` object that allows you to iterate through the paginated search results.

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


The `SearchItem` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `score` | `Optional[float]` | **NOTE**: Marengo 3.0 and newer versions do not return this field. Use the `rank` field instead.<br/><br/>The score indicating how well the clip matches the search query. |
| `start` | `Optional[float]` | The start time of the clip in seconds. |
| `end` | `Optional[float]` | The end time of the clip in seconds. |
| `video_id` | `Optional[str]` | The unique identifier of the video. Once the platform indexes a video, it assigns a unique identifier. |
| `confidence` | `Optional[str]` | **NOTE**: Marengo 3.0 and newer versions do not return this field. Use the `rank` field instead.<br/><br/>The confidence level of the match (high, medium, low). |
| `rank` | `Optional[int]` | **NOTE** : Only Marengo 3.0 and newer versions return this field. Earlier versions return `score` and `confidence` instead.<br/><br/>The relevance ranking assigned by the model. Lower numbers indicate higher relevance, starting with 1 for the most relevant result. |
| `thumbnail_url` | `Optional[str]` | The URL of the thumbnail image for the clip. |
| `transcription` | `Optional[str]` | A transcription of the spoken words that are captured in the video. |
| `id` | `Optional[str]` | The unique identifier of the video. Only appears when the `group_by=video` parameter is used in the request. |
| `user_metadata` | `Optional[typing.Dict[str, typping.Optional[typing.Any]]]` | User-defined metadata associated with the video. |
| `clips` | `Optional[List[SearchItemClipsItem]]` | An array that contains detailed information about the clips that match your query. The platform returns this array only when the `group_by` parameter is set to `video` in the request. |

The `SearchItemClipsItem` class contains the following properties:
| Name | Type | Description |
| -------- | -------- | ----------------------------------------------------------------- |
| `score` | `Optional[float]` | T**NOTE**: Marengo 3.0 and newer versions do not return this field. Use the `rank` field instead.<br/><br/>The score indicating how well the clip matches the search query. |
| `start` | `Optional[float]` | The start time of the clip in seconds. |
| `end` | `Optional[float]` | The end time of the clip in seconds. |
| `confidence` | `Optional[str]` | **NOTE**: Marengo 3.0 and newer versions do not return this field. Use the `rank` field instead.<br/><br/>The confidence level of the match (high, medium, low). |
| `rank` | `Optional[int]` | **NOTE** : Only Marengo 3.0 and newer versions return this field. Earlier versions return `score` and `confidence` instead.<br/><br/>The relevance ranking assigned by the model. Lower numbers indicate higher relevance, starting with 1 for the most relevant result. |
| `thumbnail_url` | `Optional[str]` | The URL of the thumbnail image for the clip. |
| `transcription` | `Optional[str]` | A transcription of the spoken words that are captured in the clip. |
| `video_id` | `Optional[str]` | The unique identifier of the video for the corresponding clip. |
| `user_metadata` | `Optional[typing.Dict[str, typping.Optional[typing.Any]]]` | User-defined metadata associated with the video. |

**API Reference**:  [Any-to-video search](/v1.3/api-reference/any-to-video-search/make-search-request).

**Related guides**:

- [Search](/v1.3/docs/guides/search)
- [Sorting](/v1.3/docs/guides/search/sorting)
- [Filtering](/v1.3/docs/guides/search/filtering)
- [Grouping](/v1.3/docs/guides/search/grouping)

# Error codes

This section lists the most common error messages you may encounter while performing search requests.

- `search_option_not_supported`
  - Search option `{search_option}` is not supported for index `{index_id}`. Please use one of the following search options: `{supported_search_option}`.
- `search_option_combination_not_supported`
  - Search option `{search_option}` is not supported with `{other_combination}`.
- `search_filter_invalid`
  - Filter used in search is invalid. Please use the valid filter syntax by following filtering documentation.
- `search_page_token_expired`
  - The token that identifies the page to be retrieved is expired or invalid. You must make a new search request. Token: `{next_page_token}`.
- `index_not_supported_for_search`: 
  - You can only perform search requests on indexes with an engine from the Marengo family enabled.

For a list of errors specific to this endpoint and general errors that apply to all endpoints, see the [Error codes](/v1.3/api-reference/error-codes) page.
