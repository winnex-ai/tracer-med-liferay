# Example 01 -- Portlet: Semantic Clinical Search with Proof

**Winnex AI | Klenio Padilha** . Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47) . pay@winnex.ai . BSL 1.1

---

## What this example does

A complete **Portlet MVC** that lets a logged-in Liferay user search clinical
records with a **mathematical soundness guarantee**. It is the production
pattern used by Tracer-MED:

1. The user types a clinical query (e.g. "hypertension management") and
   optionally filters by **ICD-10** and **department**.
2. The portlet resolves the tenant from the authenticated user
   (`liferay-{companyId}`).
3. It calls `MadhavaService.search(...)` (the OSGi bridge).
4. It renders the results **with the proof**:
   - `0 bound violations` -> nothing relevant was lost
   - `bound pairs` -> how many documents were evaluated with a bound

---

## The files

```
example-01-portlet/
+-- src/main/java/com/winnex/tracermed/examples/
|   +-- SearchPortlet.java              <- the Portlet component
|   +-- SearchMVCActionCommand.java     <- handles the form submission
|   +-- SearchPortletKeys.java          <- portlet keys
|   +-- MadhavaDocumentVO.java          <- view object (optional)
+-- src/main/resources/META-INF/resources/
    +-- init.jsp
    +-- view.jsp                        <- the UI
```

---

## Step 1 -- The portlet component

```java
/*
 * Business Source License 1.1 (BSL 1.1)
 * Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
 * Contact: pay@winnex.ai
 */
package com.winnex.tracermed.examples;

import com.winnex.madhava.api.api.MadhavaService;

import com.liferay.portal.kernel.portlet.bridges.mvc.MVCPortlet;

import javax.portlet.Portlet;

import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Reference;

/**
 * Example 01 -- Semantic Clinical Search with Proof.
 *
 * <p>Consumes the Madhava OSGi service (the bridge to the Python
 * microservice) and renders triage results with the mathematical proof.</p>
 *
 * @author Winnex AI | Klenio Padilha
 */
@Component(
    immediate = true,
    property = {
        "com.liferay.portlet.display-category=category.winnex",
        "com.liferay.portlet.header-portlet-css=/css/main.css",
        "com.liferay.portlet.instanceable=true",
        "javax.portlet.display-name=Tracer-MED Search (Example 01)",
        "javax.portlet.init-param.template-path=/",
        "javax.portlet.init-param.view-template=/view.jsp",
        "javax.portlet.name=" + SearchPortletKeys.SEARCH_PORTLET,
        "javax.portlet.resource-bundle=content.Language",
        "javax.portlet.security-role-ref=power-user,user"
    },
    service = Portlet.class
)
public class SearchPortlet extends MVCPortlet {

    /**
     * The Madhava bridge -- injected by OSGi. The portlet never talks HTTP
     * directly; it always goes through this service.
     */
    @Reference
    protected volatile MadhavaService madhavaService;

}
```

---

## Step 2 -- The action command (form submission)

```java
package com.winnex.tracermed.examples;

import com.winnex.madhava.api.api.MadhavaService;
import com.winnex.madhava.api.dto.MadhavaSearchRequest;
import com.winnex.madhava.api.dto.MadhavaSearchResponse;

import com.liferay.portal.kernel.portlet.bridges.mvc.BaseMVCActionCommand;
import com.liferay.portal.kernel.portlet.bridges.mvc.MVCActionCommand;
import com.liferay.portal.kernel.theme.ThemeDisplay;
import com.liferay.portal.kernel.util.ParamUtil;
import com.liferay.portal.kernel.util.WebKeys;

import javax.portlet.ActionRequest;
import javax.portlet.ActionResponse;
import javax.portlet.PortletSession;

import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Reference;

/**
 * Handles the triage form submission.
 *
 * @author Winnex AI | Klenio Padilha
 */
@Component(
    immediate = true,
    property = {
        "javax.portlet.name=" + SearchPortletKeys.SEARCH_PORTLET,
        "mvc.command.name=search"
    },
    service = MVCActionCommand.class
)
public class SearchMVCActionCommand extends BaseMVCActionCommand {

    @Override
    protected void doProcessAction(
            ActionRequest actionRequest, ActionResponse actionResponse)
        throws Exception {

        // 1. Read the form fields
        String query      = ParamUtil.getString(actionRequest, "query", "");
        String cid10      = ParamUtil.getString(actionRequest, "cid10", "");
        String department = ParamUtil.getString(actionRequest, "department", "");
        int k             = ParamUtil.getInteger(actionRequest, "k", 5);

        if ((k < 1) || (k > 50)) {
            k = 5;
        }

        if (query.trim().isEmpty()) {
            actionResponse.setRenderParameter("mvcRenderCommandName", "/");
            return;
        }

        // 2. Resolve the tenant from the authenticated user's company
        ThemeDisplay themeDisplay =
            (ThemeDisplay)actionRequest.getAttribute(WebKeys.THEME_DISPLAY);

        String tenantId = "liferay-default";
        if (themeDisplay != null) {
            tenantId = "liferay-" + themeDisplay.getCompanyId();
        }

        // 3. Build the request and call the Madhava bridge
        MadhavaSearchRequest request =
            new MadhavaSearchRequest(query, k, tenantId);
        request.setCid10(cid10);
        request.setDepartment(department);

        MadhavaSearchResponse response = _madhavaService.search(request);

        // 4. Store the response for the view
        PortletSession session = actionRequest.getPortletSession();
        session.setAttribute(
            "madhava_response", response, PortletSession.PORTLET_SCOPE);
        session.setAttribute("last_query", query, PortletSession.PORTLET_SCOPE);

        actionResponse.setRenderParameter("mvcRenderCommandName", "/");
    }

    @Reference
    protected volatile MadhavaService _madhavaService;

}
```

---

## Step 3 -- The view (view.jsp)

```jsp
<%@ include file="/init.jsp" %>

<%
com.winnex.madhava.api.dto.MadhavaSearchResponse madhavaResponse =
    (com.winnex.madhava.api.dto.MadhavaSearchResponse)session.getAttribute(
        "madhava_response");
String lastQuery = (String)session.getAttribute("last_query");
if (lastQuery == null) lastQuery = "";
boolean hasResults = (madhavaResponse != null);
%>

<div class="container-fluid tracer-med">
    <%-- Winnex brand --%>
    <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:#003056;border-radius:8px;">
        <img src="<%=request.getContextPath()%>/logo-winnex.webp"
             alt="Winnex AI" width="140" height="56" style="object-fit:contain;"/>
        <div>
            <h4 style="margin:0;color:#fff;">Tracer-MED &mdash; Semantic Clinical Search</h4>
            <p style="margin:2px 0 0;color:#cfe3f5;font-size:13px;">
                Winnex AI &bull; winnex.ai &bull; pay@winnex.ai
            </p>
        </div>
    </div>

    <p class="text-muted">
        Engine: <strong>winnex-madhava</strong> (Cauchy-Schwarz bound, 0 false
        negatives by construction). Every excluded record carries proof it
        could not be in the top-K.
    </p>

    <liferay-portlet:actionURL name="search" varImpl="searchAction" />

    <aui:form action="<%=searchAction%>" method="post" name="triageForm">
        <aui:input label="Clinical query" name="query" type="text"
            value="<%=lastQuery%>" placeholder="e.g. hypertension management" />
        <div class="row">
            <div class="col-md-4">
                <aui:input label="ICD-10" name="cid10" type="text" placeholder="e.g. I10" />
            </div>
            <div class="col-md-4">
                <aui:input label="Department" name="department" type="text"
                    placeholder="e.g. Cardiology" />
            </div>
            <div class="col-md-2">
                <aui:input label="Top-K" name="k" type="number" value="5" />
            </div>
        </div>
        <aui:button type="submit" value="Search with proof" cssClass="btn-primary" />
    </aui:form>

    <% if (hasResults) { %>
        <hr />
        <h5>Results <small>(query: <%=HtmlUtil.escape(lastQuery)%>)</small></h5>

        <% if (madhavaResponse.isSound()) { %>
            <div class="alert alert-success">
                <strong>Sound proof:</strong> 0 bound violations (no relevant
                record lost). Bound pairs evaluated:
                <%=madhavaResponse.getBoundPairs()%>.
                Engine: <%=madhavaResponse.getEngine()%>.
            </div>
        <% } else { %>
            <div class="alert alert-danger">
                <strong>BOUND VIOLATION &mdash; investigate.</strong>
            </div>
        <% } %>

        <table class="table table-striped">
            <thead>
                <tr><th>#</th><th>ID</th><th>Preview</th><th>Metadata</th></tr>
            </thead>
            <tbody>
            <% int i = 0;
                for (com.winnex.madhava.api.dto.MadhavaDocument doc
                    : madhavaResponse.getResults()) { i++; %>
                <tr>
                    <td><%=i%></td>
                    <td><%=doc.getExternalId()%></td>
                    <td><%=doc.getTextPreview()%></td>
                    <td><%=doc.getMetadata()%></td>
                </tr>
            <% } %>
            </tbody>
        </table>
    <% } else { %>
        <div class="alert alert-info">
            Enter a clinical query to start triage with proof. (The corpus
            must be indexed in the Madhava service.)
        </div>
    <% } %>
</div>
```

---

## Step 4 -- build.gradle

```gradle
dependencies {
    compileOnly project(":modules:winnex-madhava-api")
    compileOnly group: "com.liferay.portal", name: "release.portal.api"
}
```

---

## How to deploy and test

```bash
# Build
./gradlew :modules:example-01-portlet:jar

# Deploy (hot deploy into the running Liferay)
cp modules/example-01-portlet/build/libs/*.jar /opt/liferay/deploy/

# Wait for "STARTED" in the Liferay log
tail -f /opt/liferay/logs/liferay.*.log | grep STARTED

# Add the portlet: Liferay -> Add -> Widgets -> Winnex -> "Tracer-MED Search"
```

---

## What you should observe

1. Search "hypertension management" with `ICD-10 = I10`.
2. The results table shows the hypertension record first.
3. The green banner proves **0 bound violations** -- the guarantee.

---

*Winnex AI -- BSL 1.1 . pay@winnex.ai . CNPJ 58.364.637/0001-47*
