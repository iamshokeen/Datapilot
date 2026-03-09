import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * @typedef {Object} ConnectRequest
 * @property {string} alias
 * @property {string} host
 * @property {number} port
 * @property {string} database
 * @property {string} username
 * @property {string} password
 * @property {string[]} schemas
 */

/**
 * @typedef {Object} ConnectResponse
 * @property {string} connection_id
 * @property {string} alias
 * @property {string} database_name
 * @property {number} total_tables
 * @property {string[]} tables
 * @property {string} message
 */

/**
 * @typedef {Object} AgentAskRequest
 * @property {string} connection_id
 * @property {string} question
 * @property {string} [session_id]
 */

/**
 * @typedef {Object} ChartSuggestion
 * @property {string} type
 * @property {string} [x_axis]
 * @property {string} [y_axis]
 * @property {string} [group_by]
 * @property {string} reason
 */

/**
 * @typedef {Object} SubQuestionResult
 * @property {string} sub_question
 * @property {string} sql
 * @property {number} row_count
 * @property {boolean} execution_success
 * @property {number} retries
 */

/**
 * @typedef {Object} AgentAskResponse
 * @property {string} question
 * @property {string[]} sub_questions
 * @property {string} narrative
 * @property {ChartSuggestion} chart_suggestion
 * @property {Object[]} data
 * @property {SubQuestionResult[]} results
 * @property {number} total_rows
 * @property {number} sub_question_count
 * @property {number} processing_time_ms
 * @property {string} [session_id]
 */

/**
 * Connect to a database and index its schema
 * @param {ConnectRequest} data
 * @returns {Promise<ConnectResponse>}
 */
export async function connectDatabase(data) {
  const response = await apiClient.post('/connect', data);
  return response.data;
}

/**
 * Ask a question using the AI agent
 * @param {AgentAskRequest} data
 * @returns {Promise<AgentAskResponse>}
 */
export async function askQuestion(data) {
  const response = await apiClient.post('/agent/ask', data);
  return response.data;
}

/**
 * Health check
 * @returns {Promise<{status: string, version: string, environment: string}>}
 */
export async function healthCheck() {
  const response = await apiClient.get('/health');
  return response.data;
}

export default apiClient;
