import React from 'react';
import { User, Building, Mail, Phone, MapPin, ExternalLink } from 'lucide-react';

const ContactDisplay = ({ title, contact, type, className = '' }) => {
  const getDisplayValue = (value) => {
    return value && value.trim() ? value : 'N/A';
  };

  const getLinkedInFields = () => ({
    name: `${contact['First Name'] || ''} ${contact['Last Name'] || ''}`.trim(),
    email: contact['Email Address'],
    company: contact['Company'],
    position: contact['Position'],
    url: contact['URL'],
    connectedOn: contact['Connected On']
  });

  const getCRMFields = () => ({
    name: contact['fullname'] || `${contact['firstname'] || ''} ${contact['lastname'] || ''}`.trim(),
    email: contact['emailaddress1'],
    jobTitle: contact['jobtitle'],
    phone: contact['telephone1'],
    mobile: contact['mobilephone'],
    city: contact['address1_city'],
    country: contact['address1_country'],
    description: contact['description'],
    linkedinProfile: contact['mc_linkedin'] || contact['mc_linkedinprofile']
  });

  const fields = type === 'linkedin' ? getLinkedInFields() : getCRMFields();

  return (
    <div className={`card p-4 ${className}`}>
      <div className="flex items-center mb-3">
        <User className="w-5 h-5 mr-2 text-gray-600" />
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      </div>

      <div className="space-y-3">
        {/* Name */}
        <div className="flex items-center">
          <User className="w-4 h-4 mr-2 text-gray-500" />
          <span className="font-medium">{getDisplayValue(fields.name)}</span>
        </div>

        {/* Email */}
        {fields.email && (
          <div className="flex items-center">
            <Mail className="w-4 h-4 mr-2 text-gray-500" />
            <span className="text-sm text-gray-700">{fields.email}</span>
          </div>
        )}

        {/* Company/Position */}
        {type === 'linkedin' ? (
          <>
            {fields.company && (
              <div className="flex items-center">
                <Building className="w-4 h-4 mr-2 text-gray-500" />
                <span className="text-sm text-gray-700">{fields.company}</span>
              </div>
            )}
            {fields.position && (
              <div className="flex items-start">
                <div className="w-4 h-4 mr-2 mt-0.5"></div>
                <span className="text-sm text-gray-600">{fields.position}</span>
              </div>
            )}
          </>
        ) : (
          <>
            {fields.jobTitle && (
              <div className="flex items-center">
                <Building className="w-4 h-4 mr-2 text-gray-500" />
                <span className="text-sm text-gray-700">{fields.jobTitle}</span>
              </div>
            )}
          </>
        )}

        {/* Contact Info for CRM */}
        {type === 'crm' && (
          <>
            {fields.phone && (
              <div className="flex items-center">
                <Phone className="w-4 h-4 mr-2 text-gray-500" />
                <span className="text-sm text-gray-700">{fields.phone}</span>
              </div>
            )}
            {fields.mobile && fields.mobile !== fields.phone && (
              <div className="flex items-center">
                <Phone className="w-4 h-4 mr-2 text-gray-500" />
                <span className="text-sm text-gray-700">{fields.mobile} (mobile)</span>
              </div>
            )}
            {(fields.city || fields.country) && (
              <div className="flex items-center">
                <MapPin className="w-4 h-4 mr-2 text-gray-500" />
                <span className="text-sm text-gray-700">
                  {[fields.city, fields.country].filter(Boolean).join(', ')}
                </span>
              </div>
            )}
          </>
        )}

        {/* LinkedIn URL */}
        {((type === 'linkedin' && fields.url) || (type === 'crm' && fields.linkedinProfile)) && (
          <div className="flex items-center">
            <ExternalLink className="w-4 h-4 mr-2 text-gray-500" />
            <a
              href={type === 'linkedin' ? fields.url : fields.linkedinProfile}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-linkedin-600 hover:text-linkedin-700 truncate"
            >
              LinkedIn Profile
            </a>
          </div>
        )}

        {/* Additional info */}
        {type === 'linkedin' && fields.connectedOn && (
          <div className="text-xs text-gray-500 pt-2 border-t">
            Connected: {fields.connectedOn}
          </div>
        )}

        {type === 'crm' && fields.description && (
          <div className="text-xs text-gray-600 pt-2 border-t">
            <div className="max-h-20 overflow-y-auto">
              {fields.description}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContactDisplay;