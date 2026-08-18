# Example 05 -- Standalone: Direct HTTP Client (no Liferay)

**Winnex AI | Klenio Padilha** . Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47) . pay@winnex.ai . BSL 1.1

---

## What this example does

A **plain Java client** (no Liferay dependencies) that talks directly to the
`madhava-service` microservice over HTTP. It is the minimal contract between
any JVM application and the Winnex Madhava engine.

> **Use this when:** you want to script, batch, or build a non-Liferay
> consumer (a CLI tool, a batch job, a separate service) that still gets the
> mathematical proof.

---

## The files

```
example-05-standalone-client/
+-- src/main/java/com/winnex/madhava/client/
    +-- MadhavaHttpClient.java   <- the client (pure JDK, zero dependencies)
    +-- Main.java                <- a runnable demo
```

---

## Step 1 -- The client

```java
/*
 * Business Source License 1.1 (BSL 1.1)
 * Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
 * Contact: pay@winnex.ai
 */
package com.winnex.madhava.client;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * Minimal HTTP client for the Madhava microservice.
 *
 * <p>Zero external dependencies (pure JDK). Covers:
 * {@code GET /v1/health}, {@code POST /v1/index}, {@code POST /v1/search}.</p>
 *
 * @author Winnex AI | Klenio Padilha
 */
public class MadhavaHttpClient {

    private final String baseUrl;

    public MadhavaHttpClient(String baseUrl) {
        this.baseUrl = baseUrl.endsWith("/")
            ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
    }

    /** GET /v1/health -- returns the raw JSON. */
    public String health() throws Exception {
        return _get("/v1/health");
    }

    /** POST /v1/index -- ingests a corpus. */
    public String index(String tenantId, String corpusJson) throws Exception {
        String body = "{\"tenant_id\":\"" + tenantId + "\",\"corpus\":" + corpusJson + "}";
        return _post("/v1/index", body);
    }

    /** POST /v1/search -- searches with proof. */
    public String search(String tenantId, String queryJson, int k) throws Exception {
        String body = "{\"tenant_id\":\"" + tenantId
            + "\",\"query\":" + queryJson
            + ",\"k\":" + k + "}";
        return _post("/v1/search", body);
    }

    private String _get(String path) throws Exception {
        URL url = new URL(baseUrl + path);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(5000);
        conn.setReadTimeout(15000);
        return _read(conn);
    }

    private String _post(String path, String jsonBody) throws Exception {
        URL url = new URL(baseUrl + path);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setRequestProperty("Accept", "application/json");
        conn.setDoOutput(true);
        conn.setConnectTimeout(5000);
        conn.setReadTimeout(15000);
        try (OutputStream os = conn.getOutputStream()) {
            os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
        }
        return _read(conn);
    }

    private String _read(HttpURLConnection conn) throws Exception {
        int code = conn.getResponseCode();
        BufferedReader in = new BufferedReader(new InputStreamReader(
            (code >= 200 && code < 300) ? conn.getInputStream()
                                        : conn.getErrorStream(),
            StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = in.readLine()) != null) {
            sb.append(line);
        }
        in.close();
        return sb.toString();
    }

}
```

---

## Step 2 -- The runnable demo

```java
package com.winnex.madhava.client;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Runs a complete end-to-end demo against a live madhava-service:
 * health -> index -> search with proof.
 *
 * <p>Run: {@code java -cp . Main [baseUrl]}</p>
 *
 * @author Winnex AI | Klenio Padilha
 */
public class Main {

    public static void main(String[] args) throws Exception {
        String baseUrl = (args.length > 0) ? args[0]
                                           : "http://localhost:8600";
        MadhavaHttpClient client = new MadhavaHttpClient(baseUrl);

        // 1. Health
        System.out.println("== health ==");
        System.out.println(client.health());

        // 2. Build a tiny 32-dim corpus (6 clinical docs)
        Random rng = new Random(7);
        List<double[]> base = new ArrayList<>();
        for (int i = 0; i < 6; i++) {
            double[] v = new double[32];
            double n = 0;
            for (int j = 0; j < 32; j++) { v[j] = rng.nextGaussian(); n += v[j]*v[j]; }
            for (int j = 0; j < 32; j++) v[j] /= Math.sqrt(n);
            base.add(v);
        }

        String[] cids = {"I10","E11","I10","E78","I10","Z03"};
        String[] texts = {
            "Patient with essential hypertension, BP 150/95. ACE inhibitor.",
            "Type 2 diabetes mellitus. HbA1c 8.2%. Metformin.",
            "Cardiac evaluation, ECG normal sinus rhythm.",
            "Lipid panel. LDL 160. Recommend statin.",
            "Hypertension management: ACE inhibitor first-line.",
            "Chest radiograph: normal silhouette, clear lungs."
        };

        StringBuilder corpus = new StringBuilder("[");
        for (int i = 0; i < 6; i++) {
            if (i > 0) corpus.append(",");
            corpus.append("{")
                  .append("\"external_id\":\"MTS-").append(i + 1).append("\",")
                  .append("\"vector\":").append(_vec(base.get(i))).append(",")
                  .append("\"metadata\":{\"cid10\":\"").append(cids[i])
                  .append("\",\"text\":\"").append(texts[i]).append("\"}")
                  .append("}");
        }
        corpus.append("]");

        // 3. Index
        System.out.println("== index ==");
        System.out.println(client.index("liferay-1001", corpus.toString()));

        // 4. Search (query = doc 0 "hypertension" + noise)
        double[] q = new double[32];
        for (int j = 0; j < 32; j++) q[j] = base.get(0)[j] + 0.1 * rng.nextGaussian();
        double n = 0;
        for (int j = 0; j < 32; j++) n += q[j]*q[j];
        for (int j = 0; j < 32; j++) q[j] /= Math.sqrt(n);

        System.out.println("== search (hypertension) ==");
        String resp = client.search("liferay-1001", _vec(q), 3);
        System.out.println(resp);

        // 5. Interpret the proof
        System.out.println();
        System.out.println("== reading the proof ==");
        if (resp.contains("\"bound_violations\":0")) {
            System.out.println("SOUND: 0 bound violations (no relevant record lost).");
        } else {
            System.out.println("BOUND VIOLATION -- investigate!");
        }
    }

    private static String _vec(double[] v) {
        StringBuilder sb = new StringBuilder("[");
        for (int j = 0; j < v.length; j++) {
            if (j > 0) sb.append(",");
            sb.append((float) v[j]);
        }
        sb.append("]");
        return sb.toString();
    }

}
```

---

## Step 3 -- Build and run (no Maven needed)

```bash
# Compile (pure JDK, zero dependencies)
javac -d out \
  src/main/java/com/winnex/madhava/client/MadhavaHttpClient.java \
  src/main/java/com/winnex/madhava/client/Main.java

# Run against a live madhava-service
java -cp out com.winnex.madhava.client.Main http://localhost:8600
```

Expected output (live service):

```
== health ==
{"status":"ok","engine":"winnex-madhava 1.8.8",...}
== index ==
{"tenant_id":"liferay-1001","indexed":6,"dim":32,"engine":"winnex-madhava 1.8.8"}
== search (hypertension) ==
{"results":[...],"bound_violations":0,"bound_pairs":6,"sound":true,...}
== reading the proof ==
SOUND: 0 bound violations (no relevant record lost).
```

---

## Why this is the "contract"

This client shows exactly what the OSGi `winnex-madhava-service` does
internally: HTTP to the microservice, then the DTOs. If you understand this
client, you understand the whole bridge -- and you can implement it in any
language (Python, Node, Go) the same way.

---

*Winnex AI -- BSL 1.1 . pay@winnex.ai . CNPJ 58.364.637/0001-47*
