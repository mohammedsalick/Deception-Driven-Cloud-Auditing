/**
 * Honey-Token Security Dashboard JavaScript
 * Handles real-time updates, user interactions, and API communication
 */

class HoneyTokenDashboard {
    constructor() {
        this.autoRefreshEnabled = true;
        this.refreshInterval = 5000; // 5 seconds
        this.refreshTimer = null;
        this.lastUpdateTime = null;
        
        this.initializeEventListeners();
        this.startAutoRefresh();
        this.loadInitialData();
    }

    /**
     * Initialize all event listeners for dashboard interactions
     */
    initializeEventListeners() {
        // Auto-refresh toggle
        const autoRefreshCheckbox = document.getElementById('autoRefresh');
        autoRefreshCheckbox.addEventListener('change', (e) => {
            this.autoRefreshEnabled = e.target.checked;
            if (this.autoRefreshEnabled) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });

        // Manual refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.refreshData();
        });

        // Control buttons
        document.getElementById('startMonitoringBtn').addEventListener('click', () => {
            this.startMonitoring();
        });

        document.getElementById('stopMonitoringBtn').addEventListener('click', () => {
            this.stopMonitoring();
        });

        document.getElementById('simulateAttackBtn').addEventListener('click', () => {
            this.simulateAttack();
        });

        document.getElementById('resetSystemBtn').addEventListener('click', () => {
            this.resetSystem();
        });

        // Attack limit selector
        document.getElementById('attackLimit').addEventListener('change', () => {
            this.loadAttacks();
        });

        // Toast close button
        document.getElementById('toastClose').addEventListener('click', () => {
            this.hideNotification();
        });
    }

    /**
     * Start auto-refresh timer
     */
    startAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        this.refreshTimer = setInterval(() => {
            if (this.autoRefreshEnabled) {
                this.refreshData();
            }
        }, this.refreshInterval);
    }

    /**
     * Stop auto-refresh timer
     */
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    /**
     * Load initial dashboard data
     */
    async loadInitialData() {
        await this.refreshData();
    }

    /**
     * Refresh all dashboard data
     */
    async refreshData() {
        try {
            await Promise.all([
                this.loadSystemStatus(),
                this.loadAttacks(),
                this.loadStatistics()
            ]);
            
            this.updateLastRefreshTime();
        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showNotification('Error refreshing dashboard data', 'error');
        }
    }

    /**
     * Load system status from API
     */
    async loadSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            if (response.ok) {
                this.updateSystemStatus(data);
            } else {
                throw new Error(data.error || 'Failed to load system status');
            }
        } catch (error) {
            console.error('Error loading system status:', error);
            throw error;
        }
    }

    /**
     * Update system status display
     */
    updateSystemStatus(data) {
        // Update status indicator
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        const statusClass = data.status.toLowerCase().replace('_', '-');
        statusIndicator.className = `status-indicator ${statusClass}`;
        statusText.textContent = data.status;

        // Update status details
        document.getElementById('monitoringStatus').textContent = 
            data.monitoring_active ? 'Active' : 'Inactive';
        document.getElementById('totalAttacks').textContent = data.total_attacks;
        document.getElementById('lastAttack').textContent = 
            data.last_attack ? this.formatTimestamp(data.last_attack) : 'None';
        document.getElementById('uptime').textContent = this.formatUptime(data.uptime_seconds);
        document.getElementById('monitoredFiles').textContent = data.monitored_files;

        // Update control buttons based on monitoring status
        this.updateControlButtons(data.monitoring_active);
    }

    /**
     * Update control button states
     */
    updateControlButtons(monitoringActive) {
        const startBtn = document.getElementById('startMonitoringBtn');
        const stopBtn = document.getElementById('stopMonitoringBtn');

        if (monitoringActive) {
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }

    /**
     * Load recent attacks from API
     */
    async loadAttacks() {
        try {
            const limit = document.getElementById('attackLimit').value;
            const response = await fetch(`/api/attacks?limit=${limit}`);
            const data = await response.json();

            if (response.ok) {
                this.updateAttacksDisplay(data.attacks);
            } else {
                throw new Error(data.error || 'Failed to load attacks');
            }
        } catch (error) {
            console.error('Error loading attacks:', error);
            throw error;
        }
    }

    /**
     * Update attacks table display
     */
    updateAttacksDisplay(attacks) {
        const noAttacksMessage = document.getElementById('noAttacksMessage');
        const attacksTable = document.getElementById('attacksTable');
        const attacksTableBody = document.getElementById('attacksTableBody');

        if (attacks.length === 0) {
            noAttacksMessage.style.display = 'block';
            attacksTable.style.display = 'none';
        } else {
            noAttacksMessage.style.display = 'none';
            attacksTable.style.display = 'block';

            // Clear existing rows
            attacksTableBody.innerHTML = '';

            // Add attack rows
            attacks.forEach(attack => {
                const row = this.createAttackRow(attack);
                attacksTableBody.appendChild(row);
            });
        }
    }

    /**
     * Create a table row for an attack event
     */
    createAttackRow(attack) {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td><span class="attack-id">${attack.attack_id}</span></td>
            <td>${this.formatTimestamp(attack.timestamp)}</td>
            <td><span class="event-type ${attack.event_type}">${attack.event_type.replace('_', ' ')}</span></td>
            <td>${attack.filename}</td>
            <td>${attack.process_name} (${attack.process_id})</td>
            <td>${attack.username}</td>
            <td>${attack.ip_address}</td>
        `;

        return row;
    }

    /**
     * Load system statistics from API
     */
    async loadStatistics() {
        try {
            const response = await fetch('/api/statistics');
            const data = await response.json();

            if (response.ok) {
                this.updateStatistics(data);
            } else {
                throw new Error(data.error || 'Failed to load statistics');
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
            throw error;
        }
    }

    /**
     * Update statistics display
     */
    updateStatistics(data) {
        const stats = data.attack_statistics;
        const systemInfo = data.system_info;

        document.getElementById('statTotalAttacks').textContent = stats.total_attacks;
        document.getElementById('statMostTargeted').textContent = 
            stats.most_targeted_file || 'None';
        document.getElementById('statCommonEvent').textContent = 
            stats.most_common_event ? stats.most_common_event.replace('_', ' ') : 'None';
        document.getElementById('statMonitoredFiles').textContent = 
            systemInfo.monitored_files;
    }

    /**
     * Start monitoring service
     */
    async startMonitoring() {
        try {
            this.showLoading();
            
            const response = await fetch('/api/monitoring/start', {
                method: 'POST'
            });
            const data = await response.json();

            this.hideLoading();

            if (response.ok) {
                this.showNotification(data.message, 'success');
                await this.loadSystemStatus();
            } else {
                this.showNotification(data.error || 'Failed to start monitoring', 'error');
            }
        } catch (error) {
            this.hideLoading();
            console.error('Error starting monitoring:', error);
            this.showNotification('Error starting monitoring service', 'error');
        }
    }

    /**
     * Stop monitoring service
     */
    async stopMonitoring() {
        try {
            this.showLoading();
            
            const response = await fetch('/api/monitoring/stop', {
                method: 'POST'
            });
            const data = await response.json();

            this.hideLoading();

            if (response.ok) {
                this.showNotification(data.message, 'success');
                await this.loadSystemStatus();
            } else {
                this.showNotification(data.error || 'Failed to stop monitoring', 'error');
            }
        } catch (error) {
            this.hideLoading();
            console.error('Error stopping monitoring:', error);
            this.showNotification('Error stopping monitoring service', 'error');
        }
    }

    /**
     * Simulate an attack with step-by-step demonstration
     */
    async simulateAttack() {
        try {
            // Show simulation options modal first
            const simulationOptions = await this.showSimulationOptionsModal();
            if (!simulationOptions) {
                return; // User cancelled
            }

            this.showLoading('Running attack simulation...');
            
            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(simulationOptions)
            });
            const data = await response.json();

            this.hideLoading();

            if (response.ok && data.success) {
                // Show detailed simulation results
                this.showSimulationResults(data);
                
                // Refresh data to show the new attack
                setTimeout(() => this.refreshData(), 2000);
            } else {
                this.showNotification(data.error || 'Attack simulation failed', 'error');
                if (data.simulation_steps && data.simulation_steps.length > 0) {
                    this.showSimulationResults(data);
                }
            }
        } catch (error) {
            this.hideLoading();
            console.error('Error simulating attack:', error);
            this.showNotification('Error running attack simulation', 'error');
        }
    }

    /**
     * Show simulation options modal
     */
    async showSimulationOptionsModal() {
        return new Promise(async (resolve) => {
            // Load available honey-tokens
            let honeyTokens = [];
            try {
                const response = await fetch('/api/honey-tokens');
                const data = await response.json();
                if (response.ok) {
                    honeyTokens = data.honey_tokens;
                }
            } catch (error) {
                console.error('Error loading honey-tokens:', error);
            }

            // Create modal HTML
            const modalHtml = `
                <div class="simulation-modal-overlay">
                    <div class="simulation-modal">
                        <div class="modal-header">
                            <h3>🎯 Attack Simulation Options</h3>
                            <button class="modal-close" onclick="this.closest('.simulation-modal-overlay').remove(); resolve(null);">&times;</button>
                        </div>
                        <div class="modal-body">
                            <div class="form-group">
                                <label for="attackType">Attack Type:</label>
                                <select id="attackType" class="form-control">
                                    <option value="file_access">File Access (Read)</option>
                                    <option value="file_modification">File Modification</option>
                                    <option value="file_copy">File Copy</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="targetFile">Target Honey-Token:</label>
                                <select id="targetFile" class="form-control">
                                    <option value="">Random Selection</option>
                                    ${honeyTokens.map(token => 
                                        `<option value="${token.filename}">${token.filename} (${this.formatFileSize(token.size)})</option>`
                                    ).join('')}
                                </select>
                            </div>
                            <div class="simulation-info">
                                <p><strong>What will happen:</strong></p>
                                <ul>
                                    <li>System will record current state</li>
                                    <li>Selected attack will be executed on honey-token</li>
                                    <li>Monitoring system will detect unauthorized access</li>
                                    <li>System status will change to "UNDER ATTACK"</li>
                                    <li>Attack details will be logged and displayed</li>
                                </ul>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button class="btn btn-secondary" onclick="this.closest('.simulation-modal-overlay').remove(); resolve(null);">Cancel</button>
                            <button class="btn btn-danger" onclick="
                                const attackType = document.getElementById('attackType').value;
                                const targetFile = document.getElementById('targetFile').value;
                                this.closest('.simulation-modal-overlay').remove();
                                resolve({
                                    attack_type: attackType,
                                    target_file: targetFile || null
                                });
                            ">🚀 Run Simulation</button>
                        </div>
                    </div>
                </div>
            `;

            // Add modal to page
            const modalElement = document.createElement('div');
            modalElement.innerHTML = modalHtml;
            document.body.appendChild(modalElement);

            // Add resolve function to window for button access
            window.resolve = resolve;
        });
    }

    /**
     * Show detailed simulation results
     */
    showSimulationResults(simulationData) {
        const modalHtml = `
            <div class="simulation-results-overlay">
                <div class="simulation-results-modal">
                    <div class="modal-header">
                        <h3>🎯 Attack Simulation Results</h3>
                        <span class="simulation-id">ID: ${simulationData.simulation_id || 'N/A'}</span>
                        <button class="modal-close" onclick="this.closest('.simulation-results-overlay').remove();">&times;</button>
                    </div>
                    <div class="modal-body">
                        <!-- Summary Section -->
                        <div class="simulation-summary">
                            <div class="summary-item ${simulationData.success ? 'success' : 'error'}">
                                <span class="summary-label">Status:</span>
                                <span class="summary-value">${simulationData.success ? '✅ Success' : '❌ Failed'}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Attack Type:</span>
                                <span class="summary-value">${simulationData.summary?.attack_type || 'N/A'}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Target File:</span>
                                <span class="summary-value">${simulationData.summary?.target_file || 'N/A'}</span>
                            </div>
                            <div class="summary-item ${simulationData.summary?.attack_detected ? 'success' : 'warning'}">
                                <span class="summary-label">Detection:</span>
                                <span class="summary-value">${simulationData.summary?.attack_detected ? '✅ Detected' : '⚠️ Not Detected'}</span>
                            </div>
                        </div>

                        <!-- Before/After States -->
                        <div class="state-comparison">
                            <div class="state-before">
                                <h4>📊 Before Attack</h4>
                                <div class="state-details">
                                    <div class="state-item">
                                        <span class="state-label">Status:</span>
                                        <span class="state-value status-${simulationData.before_state?.status?.toLowerCase()}">${simulationData.before_state?.status || 'N/A'}</span>
                                    </div>
                                    <div class="state-item">
                                        <span class="state-label">Total Attacks:</span>
                                        <span class="state-value">${simulationData.before_state?.total_attacks || 0}</span>
                                    </div>
                                    <div class="state-item">
                                        <span class="state-label">Monitoring:</span>
                                        <span class="state-value">${simulationData.before_state?.monitoring_active ? '🟢 Active' : '🔴 Inactive'}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="state-arrow">➡️</div>
                            <div class="state-after">
                                <h4>📊 After Attack</h4>
                                <div class="state-details">
                                    <div class="state-item">
                                        <span class="state-label">Status:</span>
                                        <span class="state-value status-${simulationData.after_state?.status?.toLowerCase()}">${simulationData.after_state?.status || 'N/A'}</span>
                                    </div>
                                    <div class="state-item">
                                        <span class="state-label">Total Attacks:</span>
                                        <span class="state-value">${simulationData.after_state?.total_attacks || 0}</span>
                                    </div>
                                    <div class="state-item">
                                        <span class="state-label">Monitoring:</span>
                                        <span class="state-value">${simulationData.after_state?.monitoring_active ? '🟢 Active' : '🔴 Inactive'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Step-by-Step Process -->
                        <div class="simulation-steps">
                            <h4>📋 Step-by-Step Process</h4>
                            <div class="steps-timeline">
                                ${simulationData.simulation_steps?.map(step => `
                                    <div class="step-item">
                                        <div class="step-number">${step.step}</div>
                                        <div class="step-content">
                                            <div class="step-action">${step.action}</div>
                                            <div class="step-description">${step.description}</div>
                                            <div class="step-timestamp">${this.formatTimestamp(step.timestamp)}</div>
                                            ${step.details ? `
                                                <div class="step-details">
                                                    <pre>${JSON.stringify(step.details, null, 2)}</pre>
                                                </div>
                                            ` : ''}
                                        </div>
                                    </div>
                                `).join('') || '<p>No simulation steps available</p>'}
                            </div>
                        </div>

                        <!-- Attack Details -->
                        ${simulationData.attack_details?.attack_id ? `
                            <div class="attack-details">
                                <h4>🚨 Attack Details</h4>
                                <div class="details-grid">
                                    <div class="detail-item">
                                        <span class="detail-label">Attack ID:</span>
                                        <span class="detail-value">${simulationData.attack_details.attack_id}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">Timestamp:</span>
                                        <span class="detail-value">${this.formatTimestamp(simulationData.attack_details.timestamp)}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">Event Type:</span>
                                        <span class="detail-value">${simulationData.attack_details.event_type}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">Process:</span>
                                        <span class="detail-value">${simulationData.attack_details.process_name}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">User:</span>
                                        <span class="detail-value">${simulationData.attack_details.username}</span>
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-primary" onclick="this.closest('.simulation-results-overlay').remove();">Close</button>
                        <button class="btn btn-secondary" onclick="window.dashboard.refreshData();">Refresh Dashboard</button>
                    </div>
                </div>
            </div>
        `;

        // Add modal to page
        const modalElement = document.createElement('div');
        modalElement.innerHTML = modalHtml;
        document.body.appendChild(modalElement);

        // Show success notification
        if (simulationData.success) {
            this.showNotification('Attack simulation completed successfully! Check the detailed results.', 'success');
        }
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    /**
     * Reset system to clean state
     */
    async resetSystem() {
        if (!confirm('Are you sure you want to reset the system? This will clear all attack logs.')) {
            return;
        }

        try {
            this.showLoading();
            
            const response = await fetch('/api/reset', {
                method: 'POST'
            });
            const data = await response.json();

            this.hideLoading();

            if (response.ok && data.success) {
                this.showNotification('System reset successfully!', 'success');
                await this.refreshData();
            } else {
                this.showNotification(data.error || 'System reset failed', 'error');
            }
        } catch (error) {
            this.hideLoading();
            console.error('Error resetting system:', error);
            this.showNotification('Error resetting system', 'error');
        }
    }

    /**
     * Show loading overlay
     */
    showLoading(message = 'Processing...') {
        const overlay = document.getElementById('loadingOverlay');
        const loadingText = overlay.querySelector('p');
        if (loadingText) {
            loadingText.textContent = message;
        }
        overlay.style.display = 'flex';
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    }

    /**
     * Show notification toast
     */
    showNotification(message, type = 'info') {
        const toast = document.getElementById('notificationToast');
        const messageElement = document.getElementById('toastMessage');
        
        messageElement.textContent = message;
        toast.className = `notification-toast ${type} show`;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hideNotification();
        }, 5000);
    }

    /**
     * Hide notification toast
     */
    hideNotification() {
        const toast = document.getElementById('notificationToast');
        toast.classList.remove('show');
    }

    /**
     * Update last refresh time display
     */
    updateLastRefreshTime() {
        const now = new Date();
        this.lastUpdateTime = now;
        document.getElementById('lastUpdated').textContent = 
            now.toLocaleTimeString();
    }

    /**
     * Format timestamp for display
     */
    formatTimestamp(timestamp) {
        try {
            const date = new Date(timestamp);
            return date.toLocaleString();
        } catch (error) {
            return timestamp;
        }
    }

    /**
     * Format uptime seconds into human-readable format
     */
    formatUptime(seconds) {
        if (seconds < 60) {
            return `${seconds}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return `${minutes}m ${remainingSeconds}s`;
        } else if (seconds < 86400) {
            const hours = Math.floor(seconds / 3600);
            const remainingMinutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${remainingMinutes}m`;
        } else {
            const days = Math.floor(seconds / 86400);
            const remainingHours = Math.floor((seconds % 86400) / 3600);
            return `${days}d ${remainingHours}h`;
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new HoneyTokenDashboard();
});

// Handle page visibility changes to pause/resume auto-refresh
document.addEventListener('visibilitychange', () => {
    if (window.dashboard) {
        if (document.hidden) {
            window.dashboard.stopAutoRefresh();
        } else if (window.dashboard.autoRefreshEnabled) {
            window.dashboard.startAutoRefresh();
        }
    }
});

// Handle window focus/blur for better performance
window.addEventListener('focus', () => {
    if (window.dashboard && window.dashboard.autoRefreshEnabled) {
        window.dashboard.refreshData();
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (window.dashboard) {
        // Ctrl+R or F5 for manual refresh
        if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
            e.preventDefault();
            window.dashboard.refreshData();
        }
        
        // Ctrl+Shift+S for simulate attack
        if (e.ctrlKey && e.shiftKey && e.key === 'S') {
            e.preventDefault();
            window.dashboard.simulateAttack();
        }
        
        // Ctrl+Shift+R for reset system
        if (e.ctrlKey && e.shiftKey && e.key === 'R') {
            e.preventDefault();
            window.dashboard.resetSystem();
        }
    }
});