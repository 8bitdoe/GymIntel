Request structured JSON responses when you analyze video content. This feature returns predictable, machine-readable data that integrates directly into your applications.

Key features:
- **Control response structure**: Define exactly how you want your video analysis results formatted using JSON schemas.
- **Process responses programmatically**: Eliminate manual parsing by receiving data in predictable, machine-readable formats.
- **Validate data automatically**: Ensure response fields meet your requirements with built-in type and format validation.
- **Stream structured content**: Retrieve real-time JSON responses as analysis progresses without waiting for completion.
- **Integrate seamlessly**: Connect video analysis directly into your existing data pipelines and applications.

Use cases:
- **Directly populate data into databases**: Store video analysis results in structured tables without manual formatting.
- **Create automated reports**: Generate consistent video summaries and insights for business intelligence dashboards.
- **Build content recommendation systems**: Extract keywords and topics to power personalized content suggestions.
- **Populate content management systems**: Auto-generate video titles, descriptions, and tags in your CMS workflow.
- **Facilitate search and filtering**: Organize video metadata to make content discoverable across your platform

# Control responses

Use prompts and schemas together to control your responses:
- **The prompt** specifies what the platform must extract from the video.
- **The schema** defines the structure, field names, and data types for the response.

The schema takes precedence over the prompt. If your prompt requests a summary but your schema defines chapters, the platform returns chapters. Always ensure your prompt and schema align to request the same type of information.

## Choose your schema

A schema defines:
- **Field names**: The properties that appear in the JSON response.
- **Data types**: The type of each field (example: `string`, `number`, or `object`).
- **Required fields**: Fields that must be present in every response.
- **Nested structures**: Complex data using object definitions and references.

For complete specifications, see the [JSON schema requirements](#json-schema-requirements) section.

# Prerequisites

- You already know how to analyze videos and generate text based on their content, and you've already indexed at least one video. For instructions, see the [Analyze videos](/v1.3/docs/guides/analyze-videos) page.

# Examples

The examples in this section show different types of structured responses you can request.

<Tabs>
  <Tab title="Summaries">
    This example generates a comprehensive video summary using a simple schema.

    <CodeBlocks>
      ```Python Python maxLines=8
      import json
      from twelvelabs import TwelveLabs
      from twelvelabs.types import ResponseFormat
      
      text = client.analyze(
          video_id="<YOUR_VIDEO_ID>",
          prompt="Provide a comprehensive summary of this video.",
          response_format=ResponseFormat(
              json_schema={
                  "type": "object",
                  "properties": {
                      "summary": {"type": "string"}
                  },
                  "required": ["summary"],
              },
          ),
      )
      
      data = json.loads(text.data) if text.data else {}
      print(f"\n{data.get('summary', 'N/A')}\n")
      print(f"\nFinish Reason: {text.finish_reason}")
      ```
      
      ```typescript Node.js maxLines=8
      import { TwelveLabs } from "twelvelabs-js";
      
      const text = await client.analyze({
        videoId: "<YOUR_VIDEO_ID>",
        prompt: "Provide a comprehensive summary of this video.",
        responseFormat: {
          type: "json_schema",
          jsonSchema: {
            type: "object",
            properties: {
              summary: { type: "string" }
            },
            required: ["summary"],
          },
        },
      });
      
      
      const data = text.data ? JSON.parse(text.data) : {};
      console.log(`\n${data.summary || 'N/A'}\n`);
      console.log(`\nFinish Reason: ${text.finishReason}`);
      ```
      
    </CodeBlocks>
  </Tab>
  <Tab title="Chapters">
    This example generates video chapters with titles, summaries, and timestamps using a complex schema with nested objects.

    <CodeBlocks>
      ```Python Python maxLines=8
      import json
      from twelvelabs import TwelveLabs
      from twelvelabs.types import ResponseFormat
      
      text = client.analyze(
          video_id="<YOUR_VIDEO_ID>",
          prompt="""Provide chapters for this video. Follow these guidelines to determine the number and placement of chapters:
      
      DYNAMIC CHAPTER COUNT BASED ON DURATION:
      - For videos 0-5 minutes: Aim for 2-4 chapters
      - For videos 5-15 minutes: Aim for 4-8 chapters
      - For videos 15-30 minutes: Aim for 8-12 chapters
      - For videos 30-60 minutes: Aim for 12-20 chapters
      
      Adjust chapter count based on content complexity.
      
      CONTENT-AWARE SEGMENTATION:
      - Identify logical breaks (scene changes, topic shifts, speaker changes)
      - Ensure chapters reflect meaningful transitions""",
          response_format=ResponseFormat(
              json_schema={
                  "$defs": {
                      "Chapter": {
                          "properties": {
                              "chapter_title": {"type": "string"},
                              "chapter_summary": {"type": "string"},
                              "chapter_number": {"type": "integer"},
                              "start": {"type": "number"},
                              "end": {"type": "number"}
                          },
                          "required": [
                              "chapter_title",
                              "chapter_summary",
                              "chapter_number",
                              "start",
                              "end"
                          ],
                          "type": "object"
                      }
                  },
                  "properties": {
                      "chapters": {
                          "type": "array",
                          "items": {"$ref": "#/$defs/Chapter"}
                      }
                  },
                  "required": ["chapters"],
                  "type": "object"
              },
          ),
      )
      
      data = json.loads(text.data) if text.data else {}
      
      chapters = data.get('chapters', [])
      if chapters:
          for chapter in chapters:
              print(f"\nChapter {chapter.get('chapter_number', 'N/A')}: {chapter.get('chapter_title', 'N/A')}")
              print(f"Time: {chapter.get('start', 0):.2f}s - {chapter.get('end', 0):.2f}s")
              print(f"Summary: {chapter.get('chapter_summary', 'N/A')}")
              print("-" * 80)
      else:
          print("\nNo chapters found.\n")
      print(f"\nFinish Reason: {text.finish_reason}")
      ```
      
      ```typescript Node.js maxLines=8
      import { TwelveLabs } from "twelvelabs-js";
      
      const text = await client.analyze({
        videoId: "<YOUR_VIDEO_ID>",
        prompt: `Provide chapters for this video. Follow these guidelines to determine the number and placement of chapters:
      
      DYNAMIC CHAPTER COUNT BASED ON DURATION:
      - For videos 0-5 minutes: Aim for 2-4 chapters
      - For videos 5-15 minutes: Aim for 4-8 chapters
      - For videos 15-30 minutes: Aim for 8-12 chapters
      - For videos 30-60 minutes: Aim for 12-20 chapters
      
      Adjust chapter count based on content complexity.
      
      CONTENT-AWARE SEGMENTATION:
      - Identify logical breaks (scene changes, topic shifts, speaker changes)
      - Ensure chapters reflect meaningful transitions`,
        responseFormat: {
          type: "json_schema",
          jsonSchema: {
            $defs: {
              Chapter: {
                properties: {
                  chapter_title: { type: "string" },
                  chapter_summary: { type: "string" },
                  chapter_number: { type: "integer" },
                  start: { type: "number" },
                  end: { type: "number" }
                },
                required: [
                  "chapter_title",
                  "chapter_summary",
                  "chapter_number",
                  "start",
                  "end"
                ],
                type: "object"
              }
            },
            properties: {
              chapters: {
                type: "array",
                items: { $ref: "#/$defs/Chapter" }
              }
            },
            required: ["chapters"],
            type: "object"
          },
        },
      });
      
      const data = text.data ? JSON.parse(text.data) : {};
      
      const chapters = data.chapters || [];
      if (chapters.length > 0) {
        for (const chapter of chapters) {
          console.log(`\nChapter ${chapter.chapter_number || 'N/A'}: ${chapter.chapter_title || 'N/A'}`);
          console.log(`Time: ${(chapter.start || 0).toFixed(2)}s - ${(chapter.end || 0).toFixed(2)}s`);
          console.log(`Summary: ${chapter.chapter_summary || 'N/A'}`);
          console.log("-".repeat(80));
        }
      } else {
        console.log("\nNo chapters found.\n");
      }
      console.log(`\nFinish Reason: ${text.finishReason}`);
      ```
      
    </CodeBlocks>
  </Tab>
  <Tab title="Keywords">
    This example extracts important keywords from the video using a simple schema.

    <CodeBlocks>
      ```Python Python maxLines=8
      import json
      from twelvelabs import TwelveLabs
      from twelvelabs.types import ResponseFormat
      
      text = client.analyze(
          video_id="<YOUR_VIDEO_ID>",
          prompt="Extract and provide the most important keywords from this video.",
          response_format=ResponseFormat(
              json_schema={
                  "type": "object",
                  "properties": {
                      "keywords": {"type": "string"}
                  },
                  "required": ["keywords"],
              },
          ),
      )
      
      data = json.loads(text.data) if text.data else {}
      print(f"Keywords: {data.get('keywords', 'N/A')}\n")
      print(f"\nFinish Reason: {text.finish_reason}")
      ```
      
      ```typescript Node.js maxLines=8
      import { TwelveLabs } from "twelvelabs-js";
      
      const text = await client.analyze({
        videoId: "<YOUR_VIDEO_ID>",
        prompt: "Extract and provide the most important keywords from this video.",
        responseFormat: {
          type: "json_schema",
          jsonSchema: {
            type: "object",
            properties: {
              keywords: { type: "string" }
            },
            required: ["keywords"],
          },
        },
      });
      
      const data = text.data ? JSON.parse(text.data) : {};
      console.log(`Keywords: ${data.keywords || 'N/A'}\n`);
      console.log(`\nFinish Reason: ${text.finishReason}`);
      ```
      
    </CodeBlocks>
  </Tab>
</Tabs>

## Stream structured responses

You can receive structured JSON responses in real-time as they are generated:

<CodeBlocks>
  ```Python Python maxlines=12
  from twelvelabs import TwelveLabs
  from twelvelabs.types import ResponseFormat, StreamAnalyzeResponse_StreamEnd
  
  text_stream = client.analyze_stream(
      video_id="<YOUR_VIDEO_ID>",
      prompt="<YOUR_PROMPT>",
      response_format=ResponseFormat(
          type="json_schema",
          json_schema={
              "type": "object",
              "properties": {
                  "title": {"type": "string"},
                  "summary": {"type": "string"},
                  "keywords": {"type": "array", "items": {"type": "string"}},
              },
          },
      ),
  )
  for chunk in text_stream:
      if chunk.event_type == "text_generation":
          print(chunk.text, end="", flush=True)
      elif isinstance(chunk, StreamAnalyzeResponse_StreamEnd):
          print(f"\nFinish reason: {chunk.finish_reason}")
          if chunk.metadata and chunk.metadata.usage:
              print(f"Usage: {chunk.metadata.usage}")
  ```
  
  ```typescript Node.js maxlines=12
  
  import { TwelveLabs } from "twelvelabs-js";
  
  const textStream = await client.analyzeStream({
    videoId: "<YOUR_VIDEO_ID>",
    prompt:
      "<YOUR_PROMPT>",
    responseFormat: {
      type: "json_schema",
      jsonSchema: {
        type: "object",
        properties: {
          title: {
            type: "string",
          },
          summary: {
            type: "string",
          },
          keywords: {
            type: "array",
            items: {
              type: "string",
            },
          },
        },
      },
    },
  });
  for await (const chunk of textStream) {
    if (chunk.eventType === "text_generation" && "text" in chunk) {
      process.stdout.write(chunk.text!);
    } else if (chunk.eventType === "stream_end") {
      console.log(`\nFinish reason: ${chunk.finishReason}`);
      if (chunk.metadata && chunk.metadata.usage) {
        console.log(`Usage: ${JSON.stringify(chunk.metadata.usage)}`);
      }
    }
  }
  ```
  
</CodeBlocks>

# Best practices

- **Start with simple schemas**: Begin with basic object structures and add complexity only when needed.
- **Keep schema fields focused and related**: Schemas with unrelated fields may require multiple API calls to generate complete results. Group related analysis tasks together or make separate calls for different types of analyses.
- **Keep field names descriptive**: Use clear, consistent naming conventions for schema properties to make your code more maintainable.
- **Mark essential fields as required**: Use the `required` property to specify fields that must be present. This ensures critical data is always included in responses.
- **Handle truncated responses**: For open-ended analysis, always check the `finish_reason` field in your code. When it equals `length`, use the `max_tokens` parameter to request shorter content, and implement retry logic to avoid incomplete JSON.
- **Validate responses client-side**: Parse and validate the JSON response in your application to catch any formatting issues before processing the data.
- **Test schemas thoroughly**: Validate your schema with sample data before deploying to production. Use different video types and content lengths to ensure reliability.

# Troubleshooting

This section provides solutions to common issues you might encounter when working with structured JSON responses.

## Prompt and response mismatch

**Problem**: The response contains information different from what you requested in the prompt (for example, you asked for a summary but received chapters).

**Cause**: The schema takes precedence over the prompt. The platform generates content that matches the schema structure, regardless of what the prompt requests.

**Solution**: Ensure your prompt and schema align to request the same type of information.

## Incomplete or invalid JSON

**Problem**: The response contains truncated JSON or fails to parse.

**Cause**: The response reached the token limit before completing the JSON structure.

**Solution**: Check the `finish_reason` field. When it equals `length`, the response was truncated. Increase the `max_tokens` parameter (the maximum is 4096), simplify your schema by removing optional fields, or make your prompt more concise. For complex requests, break them into multiple API calls.

## Invalid schema error

**Problem**: You receive a `BadRequestError` with code `response_format_invalid` when making a request.

**Cause**: The schema contains unsupported constraints (such as `minLength` or `maxLength`) or invalid references (such as `$ref` pointing to non-existent definitions).

**Solution**: Review the [`json_schema`](/v1.3/api-reference/analyze-videos/analyze#request.body.response_format.json_schema) field in the API Reference section for a list of the supported constraints. Ensure all `$ref` values point to definitions in `$defs`. Remove unsupported validation keywords and use only the supported data types and constraints.

# JSON schema requirements

Your schema must adhere to the [JSON Schema Draft 2020-12 specification](https://json-schema.org/draft/2020-12) and must meet the requirements below:

- **Supported data types**: `array`, `boolean`, `integer`, `null`, `number`, `object`, and `string`.
- **Schema constraints**: Use validation keywords like `pattern` for strings, `minimum` and `maximum` for integers, `required` for objects, and `minItems` for arrays (accepts only 0 or 1).
- **Schema composition**: You can only use `anyOf` for combining schemas.
- **References**: Define subschemas in `$defs` and reference them with valid `$ref` URIs pointing to internal subschemas.

For complete schema specifications, see the [`json_schema`](/v1.3/api-reference/analyze-videos/analyze#request.body.response_format.json_schema) field in the API Reference section.
