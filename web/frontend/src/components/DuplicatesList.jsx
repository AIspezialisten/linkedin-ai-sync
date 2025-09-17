import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Filter, RefreshCw } from 'lucide-react';
import { duplicateAPI } from '../services/api';
import DuplicateCard from './DuplicateCard';

const DuplicatesList = () => {
  const [duplicates, setDuplicates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [perPage] = useState(10);

  // Filters
  const [confidenceFilter, setConfidenceFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('pending');

  useEffect(() => {
    fetchDuplicates();
  }, [currentPage, confidenceFilter, statusFilter]);

  const fetchDuplicates = async () => {
    try {
      setLoading(true);
      const response = await duplicateAPI.getDuplicates(
        currentPage,
        perPage,
        confidenceFilter || null,
        statusFilter || 'pending'
      );

      setDuplicates(response.duplicates);
      setTotal(response.total);
      setTotalPages(response.pages);
      setError(null);
    } catch (err) {
      console.error('Error fetching duplicates:', err);
      setError('Failed to load duplicates');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (duplicateId, updateData, userDecision) => {
    try {
      await duplicateAPI.approveDuplicate(duplicateId, updateData, userDecision);

      // Remove the duplicate from the list
      setDuplicates(prev => prev.filter(d => d.id !== duplicateId));
      setTotal(prev => prev - 1);

      // Show success message
      alert('Duplicate approved and CRM updated successfully!');
    } catch (error) {
      console.error('Error approving duplicate:', error);
      throw error;
    }
  };

  const handleReject = async (duplicateId, reason) => {
    try {
      await duplicateAPI.rejectDuplicate(duplicateId, reason);

      // Remove the duplicate from the list
      setDuplicates(prev => prev.filter(d => d.id !== duplicateId));
      setTotal(prev => prev - 1);

      // Show success message
      alert('Duplicate rejected successfully!');
    } catch (error) {
      console.error('Error rejecting duplicate:', error);
      throw error;
    }
  };

  const handleFlag = async (duplicateId, reason) => {
    try {
      await duplicateAPI.flagDuplicate(duplicateId, reason);

      // Remove the duplicate from the list if showing pending
      if (statusFilter === 'pending') {
        setDuplicates(prev => prev.filter(d => d.id !== duplicateId));
        setTotal(prev => prev - 1);
      }

      // Show success message
      alert('Duplicate flagged for later review!');
    } catch (error) {
      console.error('Error flagging duplicate:', error);
      throw error;
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const handleFilterChange = () => {
    setCurrentPage(1); // Reset to first page when filters change
  };

  if (loading && duplicates.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-linkedin-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Duplicate Contacts</h1>
          <p className="mt-2 text-gray-600">
            Review and manage {total} potential duplicate contacts
          </p>
        </div>
        <button
          onClick={fetchDuplicates}
          disabled={loading}
          className="btn-secondary flex items-center"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center space-x-4">
          <div className="flex items-center">
            <Filter className="w-4 h-4 mr-2 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                handleFilterChange();
              }}
              className="text-sm border border-gray-300 rounded-md px-3 py-1"
            >
              <option value="pending">Pending</option>
              <option value="flagged">Flagged</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="">All</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Confidence
            </label>
            <select
              value={confidenceFilter}
              onChange={(e) => {
                setConfidenceFilter(e.target.value);
                handleFilterChange();
              }}
              className="text-sm border border-gray-300 rounded-md px-3 py-1"
            >
              <option value="">All Confidence Levels</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="card p-4 border-red-200 bg-red-50">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      {/* Duplicates List */}
      {duplicates.length > 0 ? (
        <div className="space-y-6">
          {duplicates.map((duplicate) => (
            <DuplicateCard
              key={duplicate.id}
              duplicate={duplicate}
              onApprove={handleApprove}
              onReject={handleReject}
              onFlag={handleFlag}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="text-gray-500 text-lg mb-2">
            {loading ? 'Loading duplicates...' : 'No duplicates found'}
          </div>
          {!loading && (
            <p className="text-gray-400">
              {statusFilter === 'pending'
                ? 'All duplicates have been reviewed!'
                : 'Try adjusting your filters to see more results.'}
            </p>
          )}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between card p-4">
          <div className="text-sm text-gray-700">
            Showing {((currentPage - 1) * perPage) + 1} to {Math.min(currentPage * perPage, total)} of {total} duplicates
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="btn-secondary flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Previous
            </button>

            <div className="flex items-center space-x-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const page = i + Math.max(1, currentPage - 2);
                if (page > totalPages) return null;

                return (
                  <button
                    key={page}
                    onClick={() => handlePageChange(page)}
                    className={`px-3 py-1 text-sm rounded ${
                      page === currentPage
                        ? 'bg-linkedin-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {page}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="btn-secondary flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DuplicatesList;