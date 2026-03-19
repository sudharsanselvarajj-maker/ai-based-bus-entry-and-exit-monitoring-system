// Dashboard Controller
document.addEventListener('DOMContentLoaded', () => {
    updateSystemTime();
    setInterval(updateSystemTime, 1000);

    // Initial load
    refreshDashboard();

    // Polling for updates every 5 seconds
    setInterval(refreshDashboard, 5000);
});

async function refreshDashboard() {
    console.log('Refreshing dashboard data...');
    
    // Fetch Data
    const stats = await api.fetchStats();
    const logs = await api.fetchLogs();

    // Update Stats
    document.getElementById('stat-entries').textContent = stats.total_entries;
    document.getElementById('stat-exits').textContent = stats.total_exits;
    document.getElementById('stat-inside').textContent = stats.buses_inside;
    document.getElementById('stat-inside-main').textContent = stats.buses_inside;

    // Update Activity Table
    const tableBody = document.getElementById('activity-table-body');
    if (logs.length > 0) {
        tableBody.innerHTML = '';
        logs.forEach(log => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-slate-800/30 transition-colors';
            
            const time = new Date(log.timestamp).toLocaleString('sv-SE').replace('T', ' '); // Format: 2026-03-12 22:38:59
            const statusClass = log.event_type === 'ENTRY' ? 'text-emerald-400' : 'text-danger';

            row.innerHTML = `
                <td class="px-6 py-4 font-mono font-bold text-center">${log.plate_number}</td>
                <td class="px-6 py-4 text-slate-200 font-mono text-center">${time}</td>
                <td class="px-6 py-4 text-center">
                    <span class="font-bold uppercase ${statusClass}">${log.event_type}</span>
                </td>
            `;
            tableBody.appendChild(row);
        });

        // Update Latest Capture Card with the most recent log
        const latest = logs[0];
        document.getElementById('latest-capture-plate').textContent = latest.plate_number;
        document.getElementById('latest-capture-time').textContent = `Detected at ${new Date(latest.timestamp).toLocaleTimeString()}`;
        document.getElementById('latest-plate-badge').classList.remove('hidden');
        if (latest.image_path) {
            // Display the captured image from the backend static folder
            document.getElementById('latest-capture-img').src = `http://localhost:8000/captures/${latest.image_path}`;
        }
    } else {
        tableBody.innerHTML = '<tr><td colspan="3" class="px-6 py-10 text-center text-slate-500">No activity recorded today.</td></tr>';
    }
}

function updateSystemTime() {
    const timeElement = document.querySelector('#system-time p:first-child');
    const dateElement = document.querySelector('#system-time p:last-child');
    
    const now = new Date();
    timeElement.textContent = now.toLocaleTimeString([], { hour12: false });
    dateElement.textContent = now.toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' });
}
