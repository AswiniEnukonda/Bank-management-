// Admin Dashboard & SQL Console Logic

document.addEventListener('DOMContentLoaded', () => {
    loadAdminStats();
    loadLoansQueue();
    loadCustomersDirectory();
    loadAuditLogs();
});

async function loadAdminStats() {
    try {
        const res = await fetch('/api/admin/stats');
        if (res.status === 403) {
            window.location.href = '/';
            return;
        }
        const data = await res.json();

        document.getElementById('stat-engine').innerText = data.active_engine.toUpperCase();
        document.getElementById('stat-deposits').innerText = `$${data.total_deposits.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
        document.getElementById('stat-loans').innerText = `$${data.total_loans.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
        document.getElementById('stat-customers').innerText = data.total_customers;
        document.getElementById('stat-accounts-info').innerText = `${data.active_accounts} Active Accounts | ${data.pending_loans_count} Pending Loans`;
    } catch (e) {
        console.error("Error loading admin stats", e);
    }
}

async function loadLoansQueue() {
    const tbody = document.getElementById('admin-loans-tbody');
    try {
        const res = await fetch('/api/admin/loans');
        const data = await res.json();
        const loans = data.loans;

        if (!loans || loans.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;">No loan requests found.</td></tr>`;
            return;
        }

        tbody.innerHTML = loans.map(l => {
            let statusBadge = 'badge-warning';
            if (l.status === 'APPROVED') statusBadge = 'badge-success';
            if (l.status === 'REJECTED') statusBadge = 'badge-danger';

            let actionsHtml = '-';
            if (l.status === 'PENDING') {
                actionsHtml = `
                    <button class="btn btn-emerald" style="padding: 4px 10px; font-size: 11px;" onclick="updateLoan(${l.loan_id}, 'APPROVED')">Approve</button>
                    <button class="btn btn-danger" style="padding: 4px 10px; font-size: 11px;" onclick="updateLoan(${l.loan_id}, 'REJECTED')">Reject</button>
                `;
            }

            return `
                <tr>
                    <td>#${l.loan_id}</td>
                    <td style="font-weight:600;">${l.full_name}</td>
                    <td>@${l.username}</td>
                    <td style="font-weight:700; color: var(--accent-gold);">$${l.amount.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td>${l.term_months} Months</td>
                    <td>$${l.monthly_payment.toFixed(2)}/mo</td>
                    <td><span class="badge ${statusBadge}">${l.status}</span></td>
                    <td>${actionsHtml}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="8">Error loading loans queue.</td></tr>`;
    }
}

async function updateLoan(loan_id, status) {
    if (!confirm(`Are you sure you want to set Loan #${loan_id} to ${status}?`)) return;

    const res = await fetch('/api/admin/loans/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ loan_id, status })
    });
    const data = await res.json();
    if (data.success) {
        alert(data.message);
        loadAdminStats();
        loadLoansQueue();
        loadCustomersDirectory();
    } else {
        alert("Loan Action Failed: " + data.message);
    }
}

async function loadCustomersDirectory() {
    const tbody = document.getElementById('admin-users-tbody');
    try {
        const res = await fetch('/api/admin/customers');
        const data = await res.json();
        const users = data.users;

        tbody.innerHTML = users.map(u => `
            <tr>
                <td>#${u.user_id}</td>
                <td style="font-weight:600;">${u.username}</td>
                <td>${u.full_name}</td>
                <td>${u.email}</td>
                <td>${u.role === 'customer' ? '<span class="badge badge-blue">Customer</span>' : '<span class="badge badge-warning">Admin</span>'}</td>
                <td><span class="badge badge-success">${u.status}</span></td>
                <td style="font-size:12px; color:var(--text-muted);">${u.created_at}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7">Error loading customers.</td></tr>`;
    }
}

async function loadAuditLogs() {
    const tbody = document.getElementById('admin-audit-tbody');
    try {
        const res = await fetch('/api/admin/audit-logs');
        const data = await res.json();
        const logs = data.logs;

        tbody.innerHTML = logs.map(l => `
            <tr>
                <td>#${l.log_id}</td>
                <td>${l.username ? '@' + l.username : 'System'}</td>
                <td><span class="badge badge-blue">${l.action}</span></td>
                <td style="font-size:13px;">${l.details}</td>
                <td style="font-size:12px; font-family:monospace;">${l.ip_address}</td>
                <td style="font-size:12px; color:var(--text-muted);">${l.created_at}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6">Error loading audit logs.</td></tr>`;
    }
}

// SQL Console Logic
function setQuery(sql) {
    document.getElementById('sql-input').value = sql;
}

async function runSqlQuery() {
    const query = document.getElementById('sql-input').value.trim();
    const metricsSpan = document.getElementById('sql-metrics');
    const resultsWrapper = document.getElementById('sql-results-wrapper');
    const thead = document.getElementById('sql-results-thead');
    const tbody = document.getElementById('sql-results-tbody');

    if (!query) {
        alert("Please enter a SQL SELECT query.");
        return;
    }

    metricsSpan.innerText = "Executing query...";

    try {
        const res = await fetch('/api/admin/sql-console', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();

        if (!data.success) {
            metricsSpan.innerText = "";
            alert("SQL Execution Error: " + data.error);
            return;
        }

        const r = data.result;
        metricsSpan.innerText = `[Engine: ${r.engine.toUpperCase()}] Returned ${r.count} rows in ${r.execution_time_ms} ms`;

        // Render Table Headers
        thead.innerHTML = `<tr>${r.columns.map(c => `<th>${c}</th>`).join('')}</tr>`;

        // Render Table Rows
        if (r.rows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${r.columns.length}" style="text-align:center; color: var(--text-muted);">Query returned 0 rows.</td></tr>`;
        } else {
            tbody.innerHTML = r.rows.map(row => `
                <tr>${r.columns.map(c => `<td>${row[c] !== null ? row[c] : 'NULL'}</td>`).join('')}</tr>
            `).join('');
        }

        resultsWrapper.style.display = 'block';
    } catch (e) {
        metricsSpan.innerText = "";
        alert("Execution Error: " + e.message);
    }
}

async function logout() {
    await fetch('/api/logout');
    window.location.href = '/';
}
