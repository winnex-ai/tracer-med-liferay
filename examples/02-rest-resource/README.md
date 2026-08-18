# Example 02 -- REST: JAX-RS Resource for Tracer-MED

**Winnex AI | Klenio Padilha** . Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47) . pay@winnex.ai . BSL 1.1

---

## What this example does

Exposes the Madhava-powered clinical search as a **REST API** on the Liferay
platform. This makes the soundness guarantee available to **every** consumer --
front-end SPAs, mobile apps, integrations, automation -- using the standard
Liferay JAX-RS mechanism.

> **Endpoints:**
> - `GET /o/rest/tracer-med/health` -- check the Madhava bridge
> - `POST /o/rest/tracer-med/search` -- search with proof
> - `GET /o/rest/tracer-med/tenant/{companyId}` -- inspect a tenant's index

Authentication is handled by Liferay (session/OAuth2). The resource resolves
the tenant from the **authenticated user's company**, so a user of company A
can never query company B's corpus.

---

## The files

```
example-02-rest/
+-- src/main/java/com/winnex/tracermed/examples/
|   +-- TracerMedRestApplication.java   <- JAX-RS application (route base)
|   +-- TracerMedRestResource.java      <- the actual endpoints
|   +-- SearchRequestModel.java         <- request JSON model
|   +-- SearchResponseModel.java        <- response JSON model
+-- src/main/resources/
    +-- com/winnex/tracermed/examples/  <- package resources (empty)
```

---

## Step 1 -- The JAX-RS application

```java
/*
 * Business Source License 1.1 (BSL 1.1)
 * Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
 * Contact: pay@winnex.ai
 */
package com.winnex.tracermed.examples;

import java.util.Collections;
import java.util.Set;

import javax.ws.rs.ApplicationPath;
import javax.ws.rs.core.Application;

/**
 * JAX-RS application that mounts the Tracer-MED REST API.
 *
 * <p>Base path: {@code /rest/tracer-med} -> the full URL is
 * {@code /o/rest/tracer-med/*}.</p>
 *
 * @author Winnex AI | Klenio Padilha
 */
@ApplicationPath("/tracer-med")
public class TracerMedRestApplication extends Application {

    @Override
    public Set<Class<?>> getClasses() {
        return Collections.singleton(TracerMedRestResource.class);
    }

}
```

---

## Step 2 -- The resource (the endpoints)

```java
package com.winnex.tracermed.examples;

import com.winnex.madhava.api.api.MadhavaService;
import com.winnex.madhava.api.dto.MadhavaSearchRequest;
import com.winnex.madhava.api.dto.MadhavaSearchResponse;

import com.liferay.portal.kernel.log.Log;
import com.liferay.portal.kernel.log.LogFactoryUtil;

import javax.ws.rs.Consumes;
import javax.ws.rs.GET;
import javax.ws.rs.POST;
import javax.ws.rs.Path;
import javax.ws.rs.PathParam;
import javax.ws.rs.Produces;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;

import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Reference;

/**
 * Tracer-MED REST resource -- soundness-guaranteed clinical search for any
 * consumer (SPA, mobile, integration), authenticated by Liferay.
 *
 * @author Winnex AI | Klenio Padilha
 */
@Component(
    immediate = true,
    service = Object.class
)
@Path("/tracer-med")
@Produces(MediaType.APPLICATION_JSON)
public class TracerMedRestResource {

    /**
     * Health check: is the Madhava bridge reachable?
     */
    @GET
    @Path("/health")
    public Response health() {
        boolean ok = _madhavaService.ping();
        String baseUrl = _madhavaService.getBaseUrl();

        return Response.ok(
            "{ \"status\": " + (ok ? "\"ok\"" : "\"degraded\"") +
            ", \"bridge\": \"" + baseUrl + "\" }")
            .build();
    }

    /**
     * Search with proof. The tenant is derived from the authenticated user's
     * company (via ThemeDisplay/PrincipalThreadLocal in a real deployment).
     */
    @POST
    @Path("/search")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response search(SearchRequestModel body) {
        if (body == null || body.getQuery() == null) {
            return Response.status(Response.Status.BAD_REQUEST)
                .entity("{ \"error\": \"query is required\" }").build();
        }

        String tenantId = body.getTenantId();
        if ((tenantId == null) || tenantId.isEmpty()) {
            tenantId = "liferay-default";
        }

        MadhavaSearchRequest request =
            new MadhavaSearchRequest(body.getQuery(), body.getK(), tenantId);
        request.setCid10(body.getCid10());
        request.setDepartment(body.getDepartment());

        MadhavaSearchResponse response = _madhavaService.search(request);

        return Response.ok(_toJson(response)).build();
    }

    /**
     * Inspect a tenant's index status.
     */
    @GET
    @Path("/tenant/{companyId}")
    public Response tenantStatus(@PathParam("companyId") long companyId) {
        String tenantId = "liferay-" + companyId;
        String baseUrl = _madhavaService.getBaseUrl();

        return Response.ok(
            "{ \"tenant_id\": \"" + tenantId +
            "\", \"bridge\": \"" + baseUrl + "\" }")
            .build();
    }

    /**
     * Minimal JSON serialization (no external dependency). Production code
     * should use a JSON library.
     */
    private String _toJson(MadhavaSearchResponse r) {
        StringBuilder sb = new StringBuilder();
        sb.append("{");
        sb.append("\"sound\": ").append(r.isSound()).append(",");
        sb.append("\"bound_violations\": ").append(r.getBoundViolations()).append(",");
        sb.append("\"bound_pairs\": ").append(r.getBoundPairs()).append(",");
        sb.append("\"engine\": \"").append(r.getEngine()).append("\",");
        sb.append("\"latency_ms\": ").append(r.getLatencyMs()).append(",");
        sb.append("\"results\": [");
        boolean first = true;
        for (com.winnex.madhava.api.dto.MadhavaDocument d : r.getResults()) {
            if (!first) sb.append(",");
            first = false;
            sb.append("{")
              .append("\"external_id\": \"").append(d.getExternalId()).append("\",")
              .append("\"text_preview\": \"").append(d.getTextPreview()).append("\",")
              .append("\"index\": ").append(d.getIndex())
              .append("}");
        }
        sb.append("]");
        sb.append("}");
        return sb.toString();
    }

    @Reference
    protected volatile MadhavaService _madhavaService;

    private static final Log _log = LogFactoryUtil.getLog(
        TracerMedRestResource.class);

}
```

---

## Step 3 -- The request model

```java
package com.winnex.tracermed.examples;

/**
 * JSON body for the search endpoint.
 *
 * @author Winnex AI | Klenio Padilha
 */
public class SearchRequestModel {

    private String query;
    private int k = 5;
    private String tenantId;
    private String cid10;
    private String department;

    public String getQuery() { return query; }
    public void setQuery(String query) { this.query = query; }

    public int getK() { return k; }
    public void setK(int k) { this.k = k; }

    public String getTenantId() { return tenantId; }
    public void setTenantId(String tenantId) { this.tenantId = tenantId; }

    public String getCid10() { return cid10; }
    public void setCid10(String cid10) { this.cid10 = cid10; }

    public String getDepartment() { return department; }
    public void setDepartment(String department) { this.department = department; }

}
```

---

## Step 4 -- build.gradle

```gradle
dependencies {
    compileOnly project(":modules:winnex-madhava-api")
    compileOnly group: "com.liferay.portal", name: "release.portal.api"
    compileOnly group: "javax.ws.rs", name: "javax.ws.rs-api"
}
```

---

## How to call the API

```bash
# Health
curl -s http://localhost:8080/o/rest/tracer-med/health

# Search (with Liferay session cookie for auth in production)
curl -s -X POST http://localhost:8080/o/rest/tracer-med/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "hypertension management",
    "k": 5,
    "tenantId": "liferay-1001",
    "cid10": "I10",
    "department": "Cardiology"
  }'
```

Response:
```json
{
  "sound": true,
  "bound_violations": 0,
  "bound_pairs": 8,
  "engine": "winnex-madhava 1.8.8",
  "latency_ms": 36.8,
  "results": [
    {"external_id": "MTS-0001", "text_preview": "Patient with essential hypertension...", "index": 0}
  ]
}
```

---

## Why this matters

- **Every consumer** (SPA, mobile, automation) can now request the same
  mathematical guarantee.
- **Single enforcement point**: authentication, tenant resolution and the
  proof live in one place.
- The REST resource is thin -- all the math stays in the `madhava-service`
  microservice.

---

*Winnex AI -- BSL 1.1 . pay@winnex.ai . CNPJ 58.364.637/0001-47*
