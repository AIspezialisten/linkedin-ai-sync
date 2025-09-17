import React, { useState } from 'react';
import { CheckCircle, XCircle, Flag, AlertTriangle, ExternalLink } from 'lucide-react';
import ContactDisplay from './ContactDisplay';

const DuplicateCard = ({ duplicate, onApprove, onReject, onFlag, className = '' }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [selectedFields, setSelectedFields] = useState({});
  const [userDecision, setUserDecision] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [flagReason, setFlagReason] = useState('');
  const [loading, setLoading] = useState(false);

  const confidenceColors = {
    high: 'confidence-high',
    medium: 'confidence-medium',
    low: 'confidence-low',
    none: 'confidence-none'
  };

  const handleFieldToggle = (fieldName, value, source) => {
    setSelectedFields(prev => ({
      ...prev,
      [fieldName]: { value, source }
    }));
  };

  const handleApprove = async () => {
    if (Object.keys(selectedFields).length === 0) {
      alert('Please select at least one field to update in CRM');
      return;
    }

    setLoading(true);
    try {
      const updateData = Object.fromEntries(
        Object.entries(selectedFields).map(([key, { value }]) => [key, value])
      );

      await onApprove(duplicate.id, updateData, userDecision);
    } catch (error) {
      console.error('Error approving duplicate:', error);
      alert('Failed to approve duplicate. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    try {
      await onReject(duplicate.id, rejectReason);
    } catch (error) {
      console.error('Error rejecting duplicate:', error);
      alert('Failed to reject duplicate. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleFlag = async () => {
    setLoading(true);
    try {
      await onFlag(duplicate.id, flagReason);
    } catch (error) {
      console.error('Error flagging duplicate:', error);
      alert('Failed to flag duplicate. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getFieldComparison = () => {
    const linkedin = duplicate.linkedin_contact_data;
    const crm = duplicate.crm_contact_data;

    const comparisons = [
      {
        label: 'First Name',
        linkedin: linkedin['First Name'],
        crm: crm['firstname'],
        crmField: 'firstname'
      },
      {
        label: 'Last Name',
        linkedin: linkedin['Last Name'],
        crm: crm['lastname'],
        crmField: 'lastname'
      },
      {
        label: 'Email',
        linkedin: linkedin['Email Address'],
        crm: crm['emailaddress1'],
        crmField: 'emailaddress1'
      },
      {
        label: 'Job Title',
        linkedin: linkedin['Position'],
        crm: crm['jobtitle'],
        crmField: 'jobtitle'
      },
      {
        label: 'Company',
        linkedin: linkedin['Company'],
        crm: null,
        crmField: 'description',
        note: 'Will be added to description'
      }
    ];

    return comparisons.filter(comp => comp.linkedin || comp.crm);
  };

  return (
    <div className={`card p-6 mb-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <span className={confidenceColors[duplicate.confidence]}>
            {duplicate.confidence.toUpperCase()}
          </span>
          <span className="text-sm text-gray-600">
            {Math.round(duplicate.similarity_score * 100)}% similarity
          </span>
        </div>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-linkedin-600 hover:text-linkedin-700"
        >
          {showDetails ? 'Hide Details' : 'Show Details'}
        </button>
      </div>

      {/* AI Reasoning */}
      <div className="mb-6 p-3 bg-gray-50 rounded-lg">
        <div className="flex items-start">
          <AlertTriangle className="w-4 h-4 mr-2 mt-0.5 text-gray-500" />
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-1">AI Analysis</h4>
            <p className="text-sm text-gray-700">{duplicate.reasoning}</p>
          </div>
        </div>
      </div>

      {/* Contact Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ContactDisplay
          title="LinkedIn Contact"
          contact={duplicate.linkedin_contact_data}
          type="linkedin"
        />
        <ContactDisplay
          title="CRM Contact"
          contact={duplicate.crm_contact_data}
          type="crm"
        />
      </div>

      {/* Field-by-field comparison and selection */}
      {showDetails && (
        <div className="mb-6 border-t pt-6">
          <h4 className="text-lg font-medium mb-4">Field Comparison & Update Selection</h4>
          <div className="space-y-3">
            {getFieldComparison().map((field, index) => (
              <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex-1">
                  <div className="font-medium text-sm">{field.label}</div>
                  <div className="text-xs text-gray-600 mt-1">
                    <div>LinkedIn: {field.linkedin || 'N/A'}</div>
                    <div>CRM: {field.crm || 'N/A'}</div>
                    {field.note && <div className="text-blue-600">{field.note}</div>}
                  </div>
                </div>
                {field.linkedin && (
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={selectedFields[field.crmField]?.value === field.linkedin}
                      onChange={() => handleFieldToggle(field.crmField, field.linkedin, 'linkedin')}
                      className="mr-2"
                    />
                    <span className="text-sm">Update CRM</span>
                  </label>
                )}
              </div>
            ))}
          </div>

          {/* User decision notes */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Decision Notes (optional)
            </label>
            <textarea
              value={userDecision}
              onChange={(e) => setUserDecision(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md text-sm"
              rows={2}
              placeholder="Add any notes about your decision..."
            />
          </div>
        </div>
      )}

      {/* Matching/Conflicting Fields Summary */}
      {(duplicate.matching_fields?.length > 0 || duplicate.conflicting_fields?.length > 0) && (
        <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {duplicate.matching_fields?.length > 0 && (
            <div className="p-3 bg-green-50 rounded-lg">
              <h5 className="text-sm font-medium text-green-800 mb-2">Matching Fields</h5>
              <div className="space-y-1">
                {duplicate.matching_fields.map((field, index) => (
                  <span key={index} className="inline-block text-xs bg-green-100 text-green-800 px-2 py-1 rounded mr-1">
                    {field}
                  </span>
                ))}
              </div>
            </div>
          )}

          {duplicate.conflicting_fields?.length > 0 && (
            <div className="p-3 bg-red-50 rounded-lg">
              <h5 className="text-sm font-medium text-red-800 mb-2">Conflicting Fields</h5>
              <div className="space-y-1">
                {duplicate.conflicting_fields.map((field, index) => (
                  <span key={index} className="inline-block text-xs bg-red-100 text-red-800 px-2 py-1 rounded mr-1">
                    {field}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleApprove}
          disabled={loading || Object.keys(selectedFields).length === 0}
          className="btn-success flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <CheckCircle className="w-4 h-4 mr-2" />
          Approve & Update CRM
        </button>

        <button
          onClick={handleReject}
          disabled={loading}
          className="btn-danger flex items-center"
        >
          <XCircle className="w-4 h-4 mr-2" />
          Reject
        </button>

        <button
          onClick={handleFlag}
          disabled={loading}
          className="btn-secondary flex items-center"
        >
          <Flag className="w-4 h-4 mr-2" />
          Flag for Later
        </button>
      </div>

      {/* Reject/Flag reason inputs (shown when buttons are clicked) */}
      {showDetails && (
        <div className="mt-4 space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reject Reason (optional)
            </label>
            <input
              type="text"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md text-sm"
              placeholder="Why is this not a duplicate?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Flag Reason (optional)
            </label>
            <input
              type="text"
              value={flagReason}
              onChange={(e) => setFlagReason(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md text-sm"
              placeholder="Why flag for later review?"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default DuplicateCard;