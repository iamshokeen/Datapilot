import { useState } from 'react';
import { Database, Loader2, CheckCircle2 } from 'lucide-react';
import { connectDatabase } from '../api/client';

export default function ConnectionSetup({ onConnected }) {
  const [formData, setFormData] = useState({
    alias: 'lohono-sample',
    host: 'localhost',
    port: 5433,
    database: 'datapilot',
    username: 'datapilot',
    password: 'datapilot',
    schemas: ['public']
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await connectDatabase(formData);
      onConnected(response.connection_id, response.alias, response.total_tables);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Connection failed');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'port' ? parseInt(value) || 5432 : value
    }));
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-dp-accent/10 rounded-2xl mb-4">
            <Database className="w-8 h-8 text-dp-accent" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            Connect Your Database
          </h1>
          <p className="text-gray-400">
            DataPilot will introspect your schema and build a semantic search index
          </p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Connection Alias
              </label>
              <input
                type="text"
                name="alias"
                value={formData.alias}
                onChange={handleChange}
                className="input-field"
                placeholder="my-database"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Host
                </label>
                <input
                  type="text"
                  name="host"
                  value={formData.host}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="localhost"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Port
                </label>
                <input
                  type="number"
                  name="port"
                  value={formData.port}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="5432"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Database Name
              </label>
              <input
                type="text"
                name="database"
                value={formData.database}
                onChange={handleChange}
                className="input-field"
                placeholder="postgres"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="postgres"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-red-400 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary flex items-center justify-center gap-2 py-3 text-lg"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Connecting & Indexing...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-5 h-5" />
                  Connect & Index Schema
                </>
              )}
            </button>

            <p className="text-xs text-gray-500 text-center mt-4">
              Your credentials are used only to connect to your database and are never stored
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
