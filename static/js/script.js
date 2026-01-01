document.addEventListener('DOMContentLoaded', () => {
    const expenseForm = document.getElementById('add-expense-form');
    const expensesList = document.getElementById('expense-list');
    const totalSpentEl = document.getElementById('total-spent');
    const remainingEl = document.getElementById('remaining');
    const aiPredictionEl = document.getElementById('ai-prediction');
    const aiStatusEl = document.getElementById('ai-status');
    const dateDisplay = document.getElementById('date-display');

    // Modal elements
    const modal = document.getElementById('settings-modal');
    const settingsBtn = document.getElementById('settings-btn');
    const closeBtn = document.querySelector('.close');
    const saveBudgetBtn = document.getElementById('save-budget');
    const budgetInput = document.getElementById('budget-limit');

    let chartInstance = null;

    // Initialize
    updateDate();
    fetchExpenses();
    fetchSummary();
    fetchPrediction();
    fetchBudget();

    function updateDate() {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        dateDisplay.textContent = new Date().toLocaleDateString('en-US', options);
    }

    // --- API Calls ---

    async function fetchExpenses() {
        try {
            const res = await fetch('/api/expenses');
            const expenses = await res.json();
            renderExpenses(expenses);
            updateChart(expenses);
        } catch (err) {
            console.error('Error fetching expenses:', err);
        }
    }

    async function fetchSummary() {
        try {
            const res = await fetch('/api/summary');
            const data = await res.json();

            // data keys have changed: total_spent is now Debit, effective_limit is total available
            totalSpentEl.textContent = `$${data.total_spent.toFixed(2)}`;
            remainingEl.textContent = `$${data.remaining.toFixed(2)}`;

            if (data.exceeded) {
                showToast(`⚠️ Budget Exceeded by $${data.over_budget_amount.toFixed(2)}!`);
            }

            // Color logic: Red if in debt (negative balance), Green otherwise. Independent of Budget.
            if (data.remaining < 0) {
                remainingEl.style.color = '#ef4444';
            } else {
                remainingEl.style.color = '#10b981';
            }
        } catch (err) {
            console.error('Error fetching summary:', err);
        }
    }

    async function fetchPrediction() {
        try {
            aiStatusEl.textContent = "Analyzing spending patterns...";
            const res = await fetch('/api/prediction');
            const data = await res.json();

            if (data.status === 'success') {
                aiPredictionEl.textContent = `$${data.prediction.toFixed(2)}`;
                aiStatusEl.textContent = `Trend: ${data.trend}`;
            } else {
                aiPredictionEl.textContent = "N/A";
                aiStatusEl.textContent = "Need more data (3+ days)";
            }
        } catch (err) {
            console.error('Error fetching prediction:', err);
            aiPredictionEl.textContent = "Error";
        }
    }

    async function fetchBudget() {
        try {
            const res = await fetch('/api/budget');
            const data = await res.json();
            budgetInput.value = data.limit;
        } catch (err) {
            console.error('Error fetching budget:', err);
        }
    }

    // --- UI Rendering ---

    function renderExpenses(expenses) {
        expensesList.innerHTML = '';
        expenses.forEach(exp => {
            const row = document.createElement('tr');
            // Check type for color and sign
            const isCredit = exp.type === 'Credit';
            const colorClass = isCredit ? 'text-success' : 'text-danger';
            const sign = isCredit ? '+' : '-';

            row.innerHTML = `
                <td>${exp.date}</td>
                <td><span class="category-tag ${exp.type.toLowerCase()}">${exp.type}</span></td>
                <td>${exp.description || '-'}</td>
                <td class="${colorClass}">${sign}$${exp.amount.toFixed(2)}</td>
                <td><button class="delete-btn" onclick="deleteExpense(${exp.id})"><i class="fa-solid fa-trash"></i></button></td>
            `;
            expensesList.appendChild(row);
        });
    }

    // Expose delete function to window for inline onclick
    window.deleteExpense = async (id) => {
        if (!confirm('Are you sure?')) return;
        try {
            const res = await fetch(`/api/expenses/${id}`, { method: 'DELETE' });
            if (res.ok) {
                refreshAll();
            }
        } catch (err) {
            console.error('Error deleting expense:', err);
        }
    };

    function updateChart(expenses) {
        const ctx = document.getElementById('expenseChart').getContext('2d');

        let totalCredit = 0;
        let totalDebit = 0;

        expenses.forEach(exp => {
            if (exp.type === 'Credit') totalCredit += exp.amount;
            else totalDebit += exp.amount;
        });

        if (chartInstance) {
            chartInstance.destroy();
        }

        chartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Income (Credit)', 'Expense (Debit)'],
                datasets: [{
                    data: [totalCredit, totalDebit],
                    backgroundColor: [
                        '#10b981', // Green for Credit
                        '#ef4444'  // Red for Debit
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#94a3b8' }
                    }
                }
            }
        });
    }

    // --- Event Listeners ---

    expenseForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const newExpense = {
            amount: parseFloat(document.getElementById('amount').value),
            type: document.getElementById('type').value, // Changed from category
            description: document.getElementById('description').value,
            date: document.getElementById('date').value
        };

        try {
            const res = await fetch('/api/expenses', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newExpense)
            });

            if (res.ok) {
                expenseForm.reset();
                // Set default date to today again
                // document.getElementById('date').valueAsDate = new Date(); 
                refreshAll();
            }
        } catch (err) {
            console.error('Error adding expense:', err);
        }
    });

    // Settings Modal
    settingsBtn.onclick = () => modal.style.display = "flex";
    closeBtn.onclick = () => modal.style.display = "none";
    window.onclick = (event) => {
        if (event.target == modal) modal.style.display = "none";
    };

    saveBudgetBtn.onclick = async () => {
        const limit = parseFloat(budgetInput.value);
        if (isNaN(limit)) return;

        try {
            await fetch('/api/budget', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ limit })
            });
            modal.style.display = "none";
            fetchSummary();
        } catch (err) {
            console.error('Error saving budget:', err);
        }
    };

    function refreshAll() {
        fetchExpenses();
        fetchSummary();
        fetchPrediction();
    }

    function showToast(message) {
        const toast = document.getElementById("toast");
        toast.textContent = message;
        toast.className = "toast show";
        setTimeout(() => { toast.className = toast.className.replace("show", ""); }, 3000);
    }
});
