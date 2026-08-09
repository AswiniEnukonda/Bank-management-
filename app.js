// Customer Dashboard Frontend Logic

document.addEventListener('DOMContentLoaded', () => {
    loadUserData();
});

let currentUser = null;
let currentAccounts = [];

async function loadUserData() {
    try {
        const res = await fetch('/api/user/info');
        if (res.status === 401) {
            window.location.href = '/';
            return;
        }
        const data = await res.json();
        currentUser = data.user;
        currentAccounts = data.accounts;

        // UI Updates
        document.getElementById('welcome-name').innerText = currentUser.full_name;
        document.getElementById('user-badge-name').innerText = currentUser.username;
        document.getElementById('card-holder').innerText = currentUser.full_name.toUpperCase();

        if (currentAccounts.length > 0) {
            const primary = currentAccounts[0];
            document.getElementById('card-acc-num').innerText = formatAccNumber(primary.account_number);
            document.getElementById('primary-balance').innerText = `$${primary.balance.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
            document.getElementById('card-status').innerText = primary.status.toUpperCase();

            populateAccDropdowns(currentAccounts);
            loadTransactions(primary.account_number);
        }

        loadLoans();
    } catch (e) {
        console.error("Error loading user info", e);
    }
}

function formatAccNumber(acc) {
    if (!acc || acc.length < 8) return acc;
    return `${acc.substring(0, 4)} ${acc.substring(4, 8)} ${acc.substring(8)}`;
}

function populateAccDropdowns(accounts) {
    const selects = ['deposit-acc-select', 'withdraw-acc-select', 'transfer-acc-select'];
    selects.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = accounts.map(a => `<option value="${a.account_number}">${a.account_number} (${a.account_type.toUpperCase()} - $${a.balance.toFixed(2)})</option>`).join('');
        }
    });
}

async function loadTransactions(accountNumber) {
    const tbody = document.getElementById('tx-history-tbody');
    try {
        const res = await fetch(`/api/account/${accountNumber}/transactions`);
        const data = await res.json();
        const txs = data.transactions;

        if (!txs || txs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">No transactions recorded for this account.</td></tr>`;
            return;
        }

        tbody.innerHTML = txs.map(t => {
            let badgeClass = 'badge-blue';
            if (t.transaction_type === 'DEPOSIT' || t.transaction_type === 'TRANSFER_IN' || t.transaction_type === 'LOAN_CREDIT') {
                badgeClass = 'badge-success';
            } else if (t.transaction_type === 'WITHDRAWAL' || t.transaction_type === 'TRANSFER_OUT') {
                badgeClass = 'badge-danger';
            }

            return `
                <tr>
                    <td><span class="badge ${badgeClass}">${t.transaction_type}</span></td>
                    <td style="font-weight: 700;">$${t.amount.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td>$${t.balance_after.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td>${t.reference_account || '-'}</td>
                    <td>${t.description || '-'}</td>
                    <td style="font-size: 12px; color: var(--text-muted);">${t.created_at}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6">Error loading transactions.</td></tr>`;
    }
}

async function loadLoans() {
    const tbody = document.getElementById('loans-tbody');
    try {
        const res = await fetch('/api/loans/my-loans');
        const data = await res.json();
        const loans = data.loans;

        if (!loans || loans.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted);">No loan applications submitted yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = loans.map(l => {
            let statusBadge = 'badge-warning';
            if (l.status === 'APPROVED') statusBadge = 'badge-success';
            if (l.status === 'REJECTED') statusBadge = 'badge-danger';

            return `
                <tr>
                    <td>#${l.loan_id}</td>
                    <td style="font-weight:700;">$${l.amount.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td>${l.interest_rate}%</td>
                    <td>${l.term_months} Months</td>
                    <td>$${l.monthly_payment.toFixed(2)}/mo</td>
                    <td>$${l.remaining_balance.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td><span class="badge ${statusBadge}">${l.status}</span></td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7">Error loading loans.</td></tr>`;
    }
}

// Modal Helpers
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

// Transaction Handlers
async function handleDeposit(e) {
    e.preventDefault();
    const account_number = document.getElementById('deposit-acc-select').value;
    const amount = document.getElementById('deposit-amount').value;
    const description = document.getElementById('deposit-desc').value;

    const res = await fetch('/api/account/deposit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_number, amount, description })
    });
    const data = await res.json();
    if (data.success) {
        alert(data.message);
        closeModal('modal-deposit');
        loadUserData();
    } else {
        alert("Deposit Failed: " + data.message);
    }
}

async function handleWithdraw(e) {
    e.preventDefault();
    const account_number = document.getElementById('withdraw-acc-select').value;
    const amount = document.getElementById('withdraw-amount').value;
    const description = document.getElementById('withdraw-desc').value;

    const res = await fetch('/api/account/withdraw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_number, amount, description })
    });
    const data = await res.json();
    if (data.success) {
        alert(data.message);
        closeModal('modal-withdraw');
        loadUserData();
    } else {
        alert("Withdrawal Failed: " + data.message);
    }
}

async function handleTransfer(e) {
    e.preventDefault();
    const from_account = document.getElementById('transfer-acc-select').value;
    const to_account = document.getElementById('transfer-to-acc').value;
    const amount = document.getElementById('transfer-amount').value;
    const description = document.getElementById('transfer-desc').value;

    const res = await fetch('/api/account/transfer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_account, to_account, amount, description })
    });
    const data = await res.json();
    if (data.success) {
        alert(data.message);
        closeModal('modal-transfer');
        loadUserData();
    } else {
        alert("Transfer Failed: " + data.message);
    }
}

async function handleLoan(e) {
    e.preventDefault();
    const amount = document.getElementById('loan-amount').value;
    const term_months = document.getElementById('loan-term').value;

    const res = await fetch('/api/loans/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount, term_months })
    });
    const data = await res.json();
    if (data.success) {
        alert(data.message);
        closeModal('modal-loan');
        loadUserData();
    } else {
        alert("Loan Application Failed: " + data.message);
    }
}

async function logout() {
    await fetch('/api/logout');
    window.location.href = '/';
}
