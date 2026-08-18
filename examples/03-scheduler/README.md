# Example 03 -- Scheduler: Auto-Index Worker

**Winnex AI | Klenio Padilha** . Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47) . pay@winnex.ai . BSL 1.1

---

## What this example does

A **scheduled OSGi component** that periodically re-indexes a tenant's
clinical corpus into the Madhava microservice. This keeps the search index
fresh without any human action -- the "ingestion" half of the triage loop.

> **The two halves of the system**
> 1. **Ingestion** (this example): collect documents -> embed (or pass
>    vectors) -> `POST /v1/index`.
> 2. **Retrieval** (examples 01/02): search with proof.

---

## The files

```
example-03-scheduler/
+-- src/main/java/com/winnex/tracermed/examples/
    +-- CorpusIndexerScheduler.java    <- the scheduled component
    +-- CorpusLoader.java              <- pluggable document source
    +-- CorpusDocument.java            <- a document + its vector + metadata
```

---

## Step 1 -- The corpus document model

```java
/*
 * Business Source License 1.1 (BSL 1.1)
 * Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
 * Contact: pay@winnex.ai
 */
package com.winnex.tracermed.examples;

import java.util.List;

/**
 * A clinical document ready to be indexed into Madhava.
 *
 * <p>The {@code vector} is a float embedding of the text. In production this
 * comes from an embedding model (e.g. BGE, BlueBERT). The Madhava engine
 * itself does NOT embed text -- it receives vectors.</p>
 *
 * @author Winnex AI | Klenio Padilha
 */
public class CorpusDocument {

    private final String externalId;
    private final String text;
    private final List<Float> vector;
    private final String cid10;
    private final String department;

    public CorpusDocument(
            String externalId, String text, List<Float> vector,
            String cid10, String department) {
        this.externalId = externalId;
        this.text = text;
        this.vector = vector;
        this.cid10 = cid10;
        this.department = department;
    }

    public String getExternalId() { return externalId; }
    public String getText() { return text; }
    public List<Float> getVector() { return vector; }
    public String getCid10() { return cid10; }
    public String getDepartment() { return department; }

}
```

---

## Step 2 -- The corpus loader (pluggable source)

```java
package com.winnex.tracermed.examples;

import java.util.ArrayList;
import java.util.List;

/**
 * Loads the clinical corpus for a tenant.
 *
 * <p>This is the ONLY piece you must adapt to your data source: SQL query,
 * REST call, CSV, FHIR ingest, etc. The example returns an empty corpus so it
 * compiles and runs anywhere.</p>
 *
 * @author Winnex AI | Klenio Padilha
 */
public class CorpusLoader {

    public List<CorpusDocument> load(String tenantId) {
        // TODO: fetch documents for this tenant and embed them.
        // Example (pseudo):
        //   SELECT id, text, cid10, department FROM clinical_records
        //     WHERE company_id = ?
        //   for each row: vector = embeddingModel.embed(text)
        return new ArrayList<>();
    }

}
```

---

## Step 3 -- The scheduler

```java
package com.winnex.tracermed.examples;

import com.winnex.madhava.api.api.MadhavaService;

import com.liferay.portal.kernel.log.Log;
import com.liferay.portal.kernel.log.LogFactoryUtil;

import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;

import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Reference;

/**
 * Scheduled worker that keeps a tenant's Madhava index fresh.
 *
 * <p>The {@code cron} expression runs daily at 03:17 (local). Adjust for your
 * SLA. On each tick it loads the corpus and calls the microservice
 * {@code POST /v1/index}.</p>
 *
 * @author Winnex AI | Klenio Padilha
 */
@Component(
    immediate = true,
    property = {
        "cron.expression=0 17 3 * * ?",   // every day at 03:17
        "service.vendor=Winnex AI"
    },
    service = CorpusIndexerScheduler.class
)
public class CorpusIndexerScheduler {

    @org.osgi.service.component.annotations.Activate
    protected void activate() {
        _log.info("CorpusIndexerScheduler activated (cron: daily 03:17)");
    }

    /**
     * Called by the scheduler on each cron tick.
     */
    public void run() {
        // In production, iterate over the Liferay companies (sites) that
        // subscribe to Tracer-MED.
        for (long companyId : new long[] { 1001L, 2002L }) {
            indexTenant("liferay-" + companyId);
        }
    }

    /**
     * Indexes one tenant's corpus into the Madhava microservice.
     */
    protected void indexTenant(String tenantId) {
        try {
            List<CorpusDocument> docs = new CorpusLoader().load(tenantId);
            if (docs.isEmpty()) {
                _log.info("[" + tenantId + "] nothing to index");
                return;
            }

            String json = _buildIndexBody(tenantId, docs);
            String baseUrl = _madhavaService.getBaseUrl();

            URL url = new URL(baseUrl + "/v1/index");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(60000);

            conn.getOutputStream().write(json.getBytes(StandardCharsets.UTF_8));

            int code = conn.getResponseCode();
            _log.info("[" + tenantId + "] index result HTTP " + code
                + " (" + docs.size() + " docs)");
        }
        catch (Exception e) {
            _log.error("Failed to index tenant " + tenantId, e);
        }
    }

    private String _buildIndexBody(String tenantId, List<CorpusDocument> docs) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"tenant_id\": \"").append(tenantId).append("\",\"corpus\": [");
        boolean first = true;
        for (CorpusDocument d : docs) {
            if (!first) sb.append(",");
            first = false;
            sb.append("{")
              .append("\"external_id\": \"").append(d.getExternalId()).append("\",")
              .append("\"vector\": [");
            boolean vFirst = true;
            for (Float v : d.getVector()) {
                if (!vFirst) sb.append(",");
                vFirst = false;
                sb.append(v);
            }
            sb.append("],")
              .append("\"metadata\": {")
              .append("\"cid10\": \"").append(d.getCid10()).append("\",")
              .append("\"department\": \"").append(d.getDepartment()).append("\",")
              .append("\"text\": \"").append(
                  d.getText().replace("\"", "\\\"")).append("\"")
              .append("}")
              .append("}");
        }
        sb.append("]}");
        return sb.toString();
    }

    @Reference
    protected volatile MadhavaService _madhavaService;

    private static final Log _log = LogFactoryUtil.getLog(
        CorpusIndexerScheduler.class);

}
```

---

## How the pieces fit

```
[Liferay DB / FHIR / CSV]  --CorpusLoader.load(tenant)-->  [CorpusDocument list]
                                                                  |
                                               _buildIndexBody()   |
                                                                  v
                                                         POST /v1/index
                                                          (madhava-service)
                                                                  |
                                                                  v
                                             winnex-madhava builds the index
                                             (projections + Cauchy-Schwarz residuals)
```

Once indexed, examples 01/02 can search that tenant with the proof.

---

## Configuration notes

- **Cron**: change `cron.expression` to match your ingestion SLA.
  - `0 17 3 * * ?` -- every day at 03:17
  - `0 */30 * * * ?` -- every 30 minutes
  - `0 0 12 ? * MON-FRI` -- weekdays at noon
- **Companies**: hardcoded `{1001L, 2002L}` in `run()` -- replace with a real
  enumeration of subscribed sites.

---

## build.gradle

```gradle
dependencies {
    compileOnly project(":modules:winnex-madhava-api")
    compileOnly group: "com.liferay.portal", name: "release.portal.api"
}
```

---

*Winnex AI -- BSL 1.1 . pay@winnex.ai . CNPJ 58.364.637/0001-47*
