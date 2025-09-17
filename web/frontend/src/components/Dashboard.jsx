import React, { useState, useEffect } from 'react';
import { Users, CheckCircle, XCircle, Flag, AlertTriangle, TrendingUp } from 'lucide-react';
import { duplicateAPI } from '../services/api';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [statsData, sessionsData] = await Promise.all([
        duplicateAPI.getStats(),
        duplicateAPI.getRecentSessions(5)
      ]);

      setStats(statsData);
      setSessions(sessionsData);
      setError(null);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-linkedin-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="mx-auto h-12 w-12 text-red-500 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Dashboard</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={fetchDashboardData}
          className="btn-primary"
        >
          Try Again
        </button>
      </div>
    );
  }

  const StatCard = ({ title, value, icon: Icon, color = 'text-gray-600', bgColor = 'bg-gray-50' }) => (
    <div className="card p-6">
      <div className="flex items-center">
        <div className={`${bgColor} rounded-lg p-3`}>
          <Icon className={`h-6 w-6 ${color}`} />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Duplicate Management Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Review and manage duplicate contacts between LinkedIn and CRM
        </p>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Pending Review"
          value={stats?.pending || 0}
          icon={AlertTriangle}
          color="text-yellow-600"
          bgColor="bg-yellow-50"
        />
        <StatCard
          title="Approved"
          value={stats?.approved || 0}
          icon={CheckCircle}
          color="text-green-600"
          bgColor="bg-green-50"
        />
        <StatCard
          title="Rejected"
          value={stats?.rejected || 0}
          icon={XCircle}
          color="text-red-600"
          bgColor="bg-red-50"
        />
        <StatCard
          title="Flagged"
          value={stats?.flagged || 0}
          icon={Flag}
          color="text-blue-600"
          bgColor="bg-blue-50"
        />
      </div>

      {/* Confidence Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">By Confidence Level</h3>
          <div className="space-y-4">
            {stats?.by_confidence && Object.entries(stats.by_confidence).map(([level, count]) => (
              <div key={level} className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className={`confidence-${level} mr-3`}>
                    {level.toUpperCase()}
                  </span>
                  <span className="text-sm text-gray-600">confidence</span>
                </div>
                <span className="text-lg font-medium text-gray-900">{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Sessions */}
        <div className="card p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Sync Sessions</h3>
          {sessions.length > 0 ? (
            <div className="space-y-3">
              {sessions.map((session, index) => (
                <div key={session.id || index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {session.duplicates_found || 0} duplicates found
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(session.started_at).toLocaleDateString()} at{' '}
                      {new Date(session.started_at).toLocaleTimeString()}
                    </p>
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                    session.success === 'success'
                      ? 'bg-green-100 text-green-800'
                      : session.success === 'partial'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {session.success || 'unknown'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No recent sessions</p>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="card p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Summary</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900 mb-1">
              {stats?.total_duplicates || 0}
            </div>
            <div className="text-sm text-gray-600">Total Duplicates Found</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600 mb-1">
              {stats?.updated || 0}
            </div>
            <div className="text-sm text-gray-600">CRM Records Updated</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-red-600 mb-1">
              {stats?.errors || 0}
            </div>
            <div className="text-sm text-gray-600">Errors</div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <a href="/duplicates" className="btn-primary">
            Review Pending Duplicates
          </a>
          <a href="/duplicates?status=flagged" className="btn-secondary">
            Review Flagged Items
          </a>
          <button
            onClick={fetchDashboardData}
            className="btn-secondary"
          >
            Refresh Data
          </button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;