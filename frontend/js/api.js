const API_BASE_URL = 'http://localhost:8000';

const api = {
    async fetchLogs() {
        try {
            const response = await fetch(`${API_BASE_URL}/logs/?limit=10`, { cache: 'no-store' });
            return await response.json();
        } catch (error) {
            console.error('Error fetching logs:', error);
            return [];
        }
    },

    async fetchStats() {
        try {
            const response = await fetch(`${API_BASE_URL}/logs/stats`, { cache: 'no-store' });
            return await response.json();
        } catch (error) {
            console.error('Error fetching stats:', error);
            return { total_entries: 0, total_exits: 0, buses_inside: 0 };
        }
    }
};
