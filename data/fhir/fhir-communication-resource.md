# Communication | R4 API
Source: https://github.com/cerner/fhir.cerner.com/blob/main/content/millennium/r4/clinical/request-and-response/communication.md
Retrieved: 2026-04-19 (archived GitHub repo — Cerner FHIR docs, archived May 2024)

---

## Overview

The Communication resource is a conveyance of information from one entity, a sender, to another entity, a receiver. The information includes encoded data and optionally a related Patient and a related Encounter.

The following fields are returned if valued:

* ID
* In Response To
* Status
* Category
* Priority
* Subject
* Topic
* Encounter
* Sent DateTime
* Received DateTime
* Recipient
* Sender
* Payload

### Errors

The common errors and OperationOutcomes may be returned.

## Terminology Bindings

[See Cerner FHIR terminology bindings for Communication R4]

## Extensions

### Custom Extensions

All URLs for custom extensions are defined as `https://fhir-ehr.cerner.com/r4/StructureDefinition/{id}`

| ID | Value[x] Type | Description |
|---|---|---|
| `reply-to` | Reference | Directs where replies to the communication are sent. Must be a group. |
| `email-status` | CodeableConcept | The status of the electronic communication (in-progress, completed, or received). |

## Search

Search for communications that meet supplied query parameters.

    GET /Communication?:parameters

**Notes:**
* The content of a communication is returned through the Binary resource. A reference to the payload is provided in `Communication.payload.contentReference`.
* Only a maximum of 1000 elements are returned based on the date range.

### Authorization Types

Provider: true | Patient: false | System: true

### Parameters

| Name | Required? | Type | Description |
|---|---|---|---|
| `_id` | Conditionally | token | The logical resource ID associated with the resource. Required if `category`, `-email-status`, `recipient`, and `received` are not used. Example: `489580643.0.-4.prsnl` |
| `category` | Conditionally | token | A token for a CodeableConcept for `Communication.category`. Required with `recipient`, `received`, and `-email-status` if `_id` is not used. Example: `http://terminology.hl7.org/CodeSystem/communication-category|notification` |
| `recipient:Group` or `recipient:Practitioner` | Conditionally | reference | The recipient of the communication. Required with `category`, `received`, and `-email-status` if `_id` is not used. Example: `3456783` |
| `received` | Conditionally | date | The date range that the communication falls within. Required with `category`, `recipient`, and `-email-status` if `_id` is not used. Example: `ge2017-02-01T10:30:00Z` |
| `-email-status` | Conditionally | token | The status of the email. Required with `category`, `recipient`, and `received` if `_id` is not used. Example: `http://hl7.org/fhir/task-status|in-progress` |

**Notes:**
* The `received` parameter may be provided:
  * Once with the `ge` prefix.
  * Twice with the lower value prefixed by `ge` and the higher value prefixed by `le`.
  * Must be provided with a time component.

### Example

#### Request

    GET https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Communication?_id=489580643.0.-4.prsnl

#### Response

HTTP 200 OK — returns a FHIR Bundle of Communication resources.

## Retrieve by ID

List an individual communication by its ID.

    GET /Communication/:id

### Authorization Types

Provider: true | Patient: false | System: true

### Example

#### Request

    GET https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Communication/489580643.0.-4.prsnl

#### Response

HTTP 200 OK — returns a single Communication resource.

## Create

Create a new communication.

    POST /Communication

**Notes:**
* Only the body fields in the definition table are supported. Unsupported fields are ignored, or can cause errors.

### Authorization Types

Provider: true | Patient: false | System: true

### Headers

```
Authorization: <OAuth2 Bearer Token>
Accept: application/fhir+json
Content-Type: application/fhir+json
```

### Example

#### Request

    POST https://fhir-ehr.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Communication

#### Response

```
HTTP/1.1 201 Created
Location: https://fhir-ehr.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Communication/472894781.0.-4.0
ETag: W/"0"
```

The `ETag` response header indicates the current `If-Match` version to use on subsequent updates.

## Patch

Patch an existing communication.

    PATCH /Communication/:id

**Notes:**
* This implementation follows RFC 6902, JSON Patch.
* Only operations on the paths in the definition table are supported.

### Authorization Types

Provider: true | System: true

### Headers

```
Authorization: <OAuth2 Bearer Token>
Accept: application/fhir+json
Content-Type: application/json-patch+json
If-Match: W/"<Current version of the Communication resource>"
```

### Example

#### Request

    PATCH https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Communication/123

#### Response

```
HTTP/1.1 200 OK
ETag: W/"2"
```

The `ETag` response header indicates the current `If-Match` version to use on subsequent updates.
