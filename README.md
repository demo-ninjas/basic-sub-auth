
# Basic Subscription based Aut

This is a simple library that implements a very basic authorisation of HTTP requests based on the provision of a valid "subscription" (or a prior ENTRA login).

This library is intended to protect simple demos that do not expose any *real* secrets - aka. don't use this for an actual production app, it was never built to defend against complex attack vectors.

## Configuring Subscriptions

The library currently supports a cosmosdb backed subscription store.

Subscriptions are made up of 4 key fields of data: 

```json
{
    "id": "the subscription id", 
    "name": "Name of the subscription", 
    "expiry": "When the sub expires - timestamp or yyy-mm-dd", 
    "rules": [
        {
            "name": "allow-service-host", 
            "type": "host", 
            "hosts": [
                "service.foo.org", 
                "app.bar.com"
            ]
        }
    ]
}
```

The `id` should be a difficult to guess string, and can be used by users to identify themselves (aka. if you know the `id`, then you can make requests as that subscription).
This is akin to a typical "api token" based authentication method.

The `name` field is simply a name you give to the sub, and could be used by applications to display the "name" of the logged in subscription.

The `expiry` can be one of the following values: 

* `yyy-mm-dd` - The date when the subscription expires, specified using the `yyy-mm-dd` format
* <positive number> - A timestamp (python timestamp, so seconds since the epoch), after which  the subscription expires
* `-1` - Never expire
* `-2` - Force Expired (obviously any negative number or timestamp in the past couldd be used to do this as well ;p)

The `rules` define what http requests the subscription can make - you must specify at least one rule or the subscription will be automatically denied.

### Entra User Fields

It's possible to also apply subscriptions to Entra users (who can login via their Entra login, or via the id assigned to them).

There's 2 additional fields added for Entra users: 

* `is_entra_user` - should be set to `true` when the sub is associated with an Entra user
* `entra_username` - the username of the Entra user, it's what will be used to find the subscription of the Entra user


## Subscription Rules

A subscription is granted access to requests using a set of rules (processed in order from top to bottom).

A rule is defined by 2 key fields, plus any number of optional rule specific fields:  

```json
{
    "name": "a name for your rule - can be anything", 
    "type": "the type of the rule to apply"
}
```

There is one additional field that is available to all rules: `allow: true|false` - This field defines whether this is an `allow` type or `deny` type rule.
If `allow` is `true`, then the user request *must* match the rule to be allowed to proceed to the next rule (otherwise it will be denied)
If `allow` is `false`, then ifi the request matches the rule, the request will be immediately denied (otherwise it will proceed to the next rule)

The available rule types are: 

* `host` - matching rules on the host name
* `path` - matching rules on a set of one or more paths
* `header` - matching rules on a specific request header
* `query` - matching rules on a specific request query parameter
* `cookie` - matching rules on a specific request cookie
* `method` - matching rules on the request method
* `date` - matching rules on the current date
* `allow-all` - special case, always returns "ALLOW"
* `deny-all` - special case, always returns "DENY"

Each rule type has a set of additional fields that should be specified to configure the rule.

### Host Rule

A host rule will look something like this: 

```json
 {
    "name": "Allow Foo and Bar Hosts",
    "type": "host",
    "allow_local": true,
    "hosts": [
        "*.foo.com", 
        "regex((.+\.)?bar[\d]\.com)"
    ]
}
```

The host rule has two fields that you can define: 

* `allow_local` - which when `true` adds a regex rule to enable localhost in addition to the hosts specified
* `hosts` - is an array of host expressions

You can specify a host match in one of five ways: 

* **Exact Match** - Specify the full hostname - eg. `app.foo.com`
* **Wildcard Start** - Specify a wildcard at the start of the hostname - eg. `*.foo.com` - this will match any domain *under* `foo.com`, but *not* `foo.com` itself
* **Wildcard End** - Specify a wildcard at the end of the hostname - eg. `foo.*` - this will match any TLD with the hostname `foo` - eg.  `foo.net` or `foo.com`
* **Wildcard middle** - Specify a wildcard for a middle segment of the hostname - eg. `app.*.foo.com` - will match `app.bar.foo.com`, but will only match on the single segment, so `app.bar.abc.foo.com` will *not* match
* **Regex Match** - If you wrap your match expression in `regex()` then the expression will be compiled into a regular expression and that will be used to match the hostname

### Path Rule

A path rule will look something like this: 

```json
{
    "name": "Allow API only",
    "type": "path",
    "paths": [
        "/api/*"
    ]
}
```

The path rule has one field: `paths` - which is an array of path expressions.

You can specify a path match in one of five ways: 

* **Exact Match** - Specify the full path - eg. `/api/get-value`
* **Wildcard Start** - Specify a wildcard at the start of the path - eg. `*.html` - this will match any path that *ends* with `.html`
* **Wildcard End** - Specify a wildcard at the end of the path - eg. `/api/*` - this will match any path under `/api/` - eg. `/api/get-value` or `/api/my-method`
* **Wildcard middle** - Specify a wildcard for a middle segment of the path - eg. `/api/*/get-value` - will match `/api/v1/get-value`, but will only match on the single segment, so `/api/v1/foo/get-value` will *not* match
* **Regex Match** - If you wrap your match expression in `regex()` then the expression will be compiled into a regular expression and that will be used to match the path

NB: The querystring is *not* included in the path when matching.

### Header Rule

A header rule will look something like this: 

```json
{
    "name": "Require x-context Header",
    "type": "header",
    "header": "x-context", 
    "values": [ "*" ]
}
```

The header rule has two fields: 

* `header` - The name of the header to match (or can be `header_name`) 
* `values` - An array of header value expressions (or can be `header_vals`)

You can specify a header match in one of six ways: 

* **Exact Match** - Specify the full header value - eg. `abc123`
* **Any Value Match** - Specify `*` alone, and the match will only test for the presence of the header, not the value itself
* **Wildcard Start** - Specify a wildcard at the start of the value - eg. `*ABC` - this will match any value that *ends* with `ABC` - eg. `123ABC`
* **Wildcard End** - Specify a wildcard at the end of the value - eg. `ABC*` - this will match any value that starts with `ABC` - eg. `ABC123`
* **Wildcard middle** - Specify a wildcard for the middle of the value - eg. `ABC*DEF` - will match `ABC123DEF` (note, you can only specify one wildcard when using midddle matching)
* **Regex Match** - If you wrap your match expression in `regex()` then the expression will be compiled into a regular expression and that will be used to match the value

### Query Rule

A query rule will look something like this: 

```json
{
    "name": "Require zone query",
    "type": "query",
    "param": "zone", 
    "values": [ "regex(AU|NZ|JP)" ]
}
```

The query rule has two fields: 

* `param` - The name of the query parameter to match (or can be `query`)
* `values` - An array of query value expressions (or can be `query_vals`)

You can specify a query param match in one of six ways: 

* **Exact Match** - Specify the full param value - eg. `abc123`
* **Any Value Match** - Specify `*` alone, and the match will only test for the presence of the query param, not the value itself
* **Wildcard Start** - Specify a wildcard at the start of the value - eg. `*ABC` - this will match any value that *ends* with `ABC` - eg. `123ABC`
* **Wildcard End** - Specify a wildcard at the end of the value - eg. `ABC*` - this will match any value that starts with `ABC` - eg. `ABC123`
* **Wildcard middle** - Specify a wildcard for the middle of the value - eg. `ABC*DEF` - will match `ABC123DEF` (note, you can only specify one wildcard when using midddle matching)
* **Regex Match** - If you wrap your match expression in `regex()` then the expression will be compiled into a regular expression and that will be used to match the value


### Cookie Rule

A cookie rule will look something like this: 

```json
{
    "name": "Require edible cookie",
    "type": "cookie",
    "cookie": "edible", 
    "values": [ "*" ]
}
```

The cookie rule has two fields: 

* `cookie` - The name of the cookie to match (or can be `cookie_name`)
* `values` - An array of query value expressions (or can be `cookies`)

You can specify a cookie match in one of six ways: 

* **Exact Match** - Specify the full cookie value - eg. `abc123`
* **Any Value Match** - Specify `*` alone, and the match will only test for the presence of the cookie, not the value itself
* **Wildcard Start** - Specify a wildcard at the start of the value - eg. `*ABC` - this will match any value that *ends* with `ABC` - eg. `123ABC`
* **Wildcard End** - Specify a wildcard at the end of the value - eg. `ABC*` - this will match any value that starts with `ABC` - eg. `ABC123`
* **Wildcard middle** - Specify a wildcard for the middle of the value - eg. `ABC*DEF` - will match `ABC123DEF` (note, you can only specify one wildcard when using midddle matching)
* **Regex Match** - If you wrap your match expression in `regex()` then the expression will be compiled into a regular expression and that will be used to match the value

### Method Rule

A method rule will look something like this: 

```json
{
    "name": "Allow GET and PUT only",
    "type": "method",
    "methods": [ "GET", "PUT" ]
}
```

The method rule has one field `methods` - which is an array of methods to match.

This rule only does exact matching.

### Date Rule

A date rule will  look something like this: 

```json
{
    "name": "Only from May 1",
    "type": "date",
    "date": "2025-05-01",
    "operator": ">="
}
```

The date rule has two fields: 

* `date` - The date to apply the comparison operation against (specified in `yyyy-mm-dd` or `YYYY-MM-DD HH:MM:SS` format)
* `operator` - The operator to used for the comparison

The available operators are: 

* `==` - match the exact date (alternatively `eq`, `equals` or `=`)
* `!=` - match any other date (alternatively `ne`, `not-equals` or `!`)
* `<` - match any date before (alternatively `lt` or `before`) 
* `<=` - match any date before or on the date (alternatively `le` or `until`)
* `>` - match any date after (alternatively `gt` or `after`)
* `>=` - match any date from the date onwards (alternatively `ge` or `from`)


## Configuring CosmosDB

To enable the app to reach out to the CosmosDB, specify the following environment variables: 

* `COSMOS_ENDPOINT` - The endpoint for the CosmosDB account (alternatively, you can also use: `SUBSCRIPTIONS_COSMOS_ENDPOINT` or `COSMOS_ACCOUNT_HOST` to specify this)
* `COSMOS_SUBSCRIPTION_DB` - The name of the CosmosDB Database (defaults to `subscriptions`) - You can also use `COSMOS_DB` to specify this
* `COSMOS_SUBSCRIPTION_CONTAINER` - The name of the Container that holds the subscriptions (defaults to `subscriptions`)


## Configuring Entra

If you wish to enable Entra users to login, you must specify the following environment variables:  

* `ENTRA_AUTHORITY` - The URL of the Entra Authority, likely will be something like: `https://login.microsoftonline.com/{directoryid}`
* `ENTRA_CLIENT_ID` - The client ID for this Registered App client
* `ENTRA_CLIENT_SECRET` - The client secret for this Registered App Client
* `ENTRA_APP_NAME` - The Name of this Registered App
* `ENTRA_SCOPES` [Optional] - If not specified, will default to `User.Read` 
* `ENTRA_REDIRECT_URI` [Optipnal] - If not specified, will default to `/api/auth-callback`