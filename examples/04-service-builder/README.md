# Example 04 -- Service Builder: Audit Persistence

**Winnex AI | Klenio Padilha** . Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47) . pay@winnex.ai . BSL 1.1

---

## What this example does

Persists every clinical triage (the query, the proof, the results) into the
**Liferay database** using **Service Builder**. This gives you a durable,
queryable audit trail: *who searched what, when, and with what guarantee*.

> This is the "auditability" layer on top of the Madhava proof. The proof is
> in the response; this example makes it survive in the DB.

---

## The files

```
example-04-service-builder/
+-- example-04-service-builder-service/      <- generated service module
|   +-- src/main/resources/service.xml       <- the entity definition
+-- example-04-service-builder-api/          <- generated API module
    +-- src/main/java/.../model/TriageAudit.java
```

---

## Step 1 -- Define the entity (`service.xml`)

```xml
<?xml version="1.0"?>
<!DOCTYPE service-builder PUBLIC
    "-//Liferay//DTD Service Builder 7.4.0//EN"
    "http://www.liferay.com/dtd/liferay-service-builder_7_4_0.dtd">

<service-builder dependency-injector="ds" package-path="com.winnex.tracermed.audit">
    <namespace>TracerMedAudit</namespace>

    <entity name="TriageAudit" local-service="true" remote-service="false">
        <!-- PK -->
        <column name="triageAuditId" type="long" primary="true" id-type="assigned" />

        <!-- Tenant + user context -->
        <column name="companyId" type="long" />
        <column name="userId" type="long" />
        <column name="userName" type="String" />
        <column name="tenantId" type="String" />

        <!-- The query and filters -->
        <column name="query" type="String" />
        <column name="cid10" type="String" />
        <column name="department" type="String" />
        <column name="k" type="int" />

        <!-- THE PROOF -->
        <column name="boundViolations" type="long" />
        <column name="boundPairs" type="long" />
        <column name="sound" type="boolean" />
        <column name="engine" type="String" />
        <column name="latencyMs" type="double" />

        <!-- Result preview (JSON of top docs) -->
        <column name="resultJson" type="String" />

        <!-- Timestamps -->
        <column name="createDate" type="Date" />
        <column name="modifiedDate" type="Date" />

        <!-- Find by tenant + query -->
        <finder name="CompanyId" return-type="Collection">
            <finder-column name="companyId" />
        </finder>
        <finder name="TenantId" return-type="Collection">
            <finder-column name="tenantId" />
        </finder>
        <finder name="TenantIdSound" return-type="Collection">
            <finder-column name="tenantId" />
            <finder-column name="sound" />
        </finder>
    </entity>
</service-builder>
```

---

## Step 2 -- The local service that records a triage

```java
/*
 * Business Source License 1.1 (BSL 1.1)
 * Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
 * Contact: pay@winnex.ai
 */
package com.winnex.tracermed.audit.service.impl;

import com.winnex.madhava.api.dto.MadhavaSearchResponse;
import com.winnex.tracermed.audit.model.TriageAudit;
import com.winnex.tracermed.audit.service.base.TriageAuditLocalServiceBaseImpl;

import com.liferay.portal.kernel.exception.PortalException;

import java.util.Date;

/**
 * Records every triage (query + proof + results) into the Liferay DB.
 *
 * @author Winnex AI | Klenio Padilha
 */
public class TriageAuditLocalServiceImpl
    extends TriageAuditLocalServiceBaseImpl {

    /**
     * Persist a completed triage with its proof.
     */
    public TriageAudit record(
            long companyId, long userId, String userName, String tenantId,
            String query, String cid10, String department, int k,
            MadhavaSearchResponse response, String resultJson)
        throws PortalException {

        long id = counterLocalService.increment(TriageAudit.class.getName());

        TriageAudit audit = triageAuditPersistence.create(id);

        audit.setCompanyId(companyId);
        audit.setUserId(userId);
        audit.setUserName(userName);
        audit.setTenantId(tenantId);

        audit.setQuery(query);
        audit.setCid10(cid10);
        audit.setDepartment(department);
        audit.setK(k);

        audit.setBoundViolations(response.getBoundViolations());
        audit.setBoundPairs(response.getBoundPairs());
        audit.setSound(response.isSound());
        audit.setEngine(response.getEngine());
        audit.setLatencyMs(response.getLatencyMs());
        audit.setResultJson(resultJson);

        Date now = new Date();
        audit.setCreateDate(now);
        audit.setModifiedDate(now);

        return triageAuditPersistence.update(audit);
    }

}
```

---

## Step 3 -- Using it from the portlet (example 01)

After a successful search, persist the audit:

```java
// In SearchMVCActionCommand.doProcessAction(...), after search(...):
TriageAudit audit = _triageAuditLocalService.record(
    themeDisplay.getCompanyId(),
    themeDisplay.getUserId(),
    themeDisplay.getUser().getFullName(),
    tenantId,
    query, cid10, department, k,
    response,
    _serializeResults(response));   // JSON of the top documents
```

---

## Step 4 -- Query the audit trail

```java
// All triages for a tenant where the proof held (sound = true)
List<TriageAudit> soundTriages =
    _triageAuditLocalService.getTenantIdSoundTriages(tenantId, true);

// All triages for a company
List<TriageAudit> companyTriages =
    _triageAuditLocalService.getCompanyIdTriages(companyId);
```

---

## Why this matters for regulated healthcare

- **LGPD Art. 20 / GDPR Art. 9 / HIPAA** ask for *accountability*: who
  processed what health data, when, and with what safeguard.
- This table is the **safeguard record**: each row carries the query, the
  tenant, the user, and the mathematical proof (`sound`, `bound_violations`).
- Combined with the WORM evidence chain in the microservice, you get both a
  **queryable** trail (Liferay DB) and an **immutable** trail (WORM).

---

## Generating the Service Builder code

```bash
# In the module directory
./gradlew :modules:example-04-service-builder-service:buildService
./gradlew :modules:example-04-service-builder-service:build
```

---

*Winnex AI -- BSL 1.1 . pay@winnex.ai . CNPJ 58.364.637/0001-47*
