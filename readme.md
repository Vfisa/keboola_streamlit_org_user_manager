# Keboola Project User Manager

A Streamlit web application for managing user access across Keboola projects within an organization. This app provides a user-friendly interface to view, audit, and remove user access from multiple projects simultaneously.

## Overview

This application integrates with the Keboola Management API to provide organization administrators with tools to:
- View all users across all projects in an organization
- Remove user access from selected projects
- Download user-project mappings as CSV
- Maintain an audit log of all actions performed

The app is designed to work both as a standalone Streamlit application and as a data application within the Keboola platform.

## Key Features

### 1. Multi-Stack Support
- **AWS US Virginia**: `https://connection.keboola.com`
- **GCP US Virginia**: `https://connection.us-east4.gcp.keboola.com`
- **AWS EU Frankfurt**: `https://connection.eu-central-1.keboola.com`
- **Azure EU Ireland**: `https://connection.north-europe.azure.keboola.com`
- **GCP EU Frankfurt**: `https://connection.europe-west3.gcp.keboola.com`
- **Custom**: User-defined API endpoint

### 2. User Management
- Load all users from all projects within an organization
- Filter and select users by email address
- View detailed user information including roles, creation dates, and expiration dates
- Remove users from multiple projects with a single action

### 3. Data Export
- Export complete user-project mappings as CSV
- Includes metadata: user ID, email, role, project details, creation dates, expiration dates, invitor, approver, and reason

### 4. Audit Logging
- Track all user removal actions with timestamps
- Log API calls with sanitized headers for security
- Maintain session-based audit trail

## API Endpoints Used

The application interacts with the following Keboola Management API endpoints:

### Token Verification
```
GET {API_HOST}/manage/tokens/verify
```
Verifies the provided API token and retrieves token owner information.

### Projects List
```
GET {API_HOST}/manage/organizations/{org_id}/projects
```
Retrieves all projects within the specified organization.

### Users List
```
GET {API_HOST}/manage/projects/{project_id}/users
```
Retrieves all users for a specific project.

### User Removal
```
DELETE {API_HOST}/manage/projects/{project_id}/users/{user_id}
```
Removes a user from a specific project.

## Required Libraries

### Core Dependencies
- **streamlit**: Web application framework
- **requests**: HTTP library for API calls
- **pandas**: Data manipulation and analysis
- **datetime**: Date and time handling (built-in Python library)

### Installation
```bash
pip install streamlit requests pandas
```

## Configuration and Secrets

### Required Secrets
The application expects the following secrets to be configured:

1. **keboola_api_token**: Keboola Management API token
2. **keboola_org_id**: Organization ID

### Streamlit Secrets Configuration
When running in Streamlit Cloud or as a Keboola data application, configure secrets in `.streamlit/secrets.toml`:

```toml
keboola_api_token = "your-api-token-here"
keboola_org_id = "your-org-id-here"
```

### Manual Configuration
If secrets are not configured, the application will prompt for manual input via the sidebar.

## Usage Instructions

### 1. Environment Setup
1. Select the appropriate Keboola stack from the sidebar dropdown
2. Enter your API token and organization ID (if not configured via secrets)
3. Click "Check Token" to verify your credentials

### 2. Loading Data
1. Click "Load Users" to fetch all projects and users from your organization
2. The app will display a summary of loaded data
3. Use the download button to export the complete user-project mapping

### 3. Managing User Access
1. Select a user from the email dropdown
2. Review their current project assignments
3. Select projects to remove the user from
4. Click "Remove Selected Access" to execute the changes
5. Review the audit log for confirmation

## Technical Details

### Session State Management
The application uses Streamlit's session state to maintain:
- API credentials
- Loaded project and user data
- Audit log entries

### Caching
- `@st.cache_data` is used for API calls to improve performance
- Cached functions: `get_projects()` and `get_users()`

### Error Handling
- Token validation with user feedback
- API error handling with status codes and error messages
- Input validation for API host URLs

### Security Features
- API tokens are masked in audit logs
- Password-type input field for API token
- Headers are sanitized before logging

## Keboola Integration

This application is designed to work seamlessly as a Keboola data application:

1. **Secrets Management**: Automatically loads API credentials from Keboola's secret manager
2. **Multi-Stack Support**: Works with all Keboola deployment regions
3. **Data Export**: Exports data in CSV format compatible with Keboola's data pipeline
4. **Audit Trail**: Maintains detailed logs for compliance and monitoring

## Data Schema

The application generates a comprehensive user-project mapping with the following fields:

- **user_id**: Unique user identifier
- **email**: User's email address
- **role**: User's role in the project
- **project**: Project name
- **project_id**: Unique project identifier
- **organization_id**: Organization identifier
- **expires**: User access expiration date
- **created**: User creation timestamp
- **reason**: Reason for user access (if available)
- **invitor**: Email of the user who sent the invitation
- **approver**: Email of the user who approved the access

## Running the Application

### Local Development
```bash
streamlit run app.py
```

### Keboola Data Application
Deploy as a Keboola data application with the following configuration:
- Set required secrets in the Keboola UI
- Configure the application parameters as needed
- The app will automatically detect the Keboola environment

## Troubleshooting

### Common Issues
1. **Invalid Token**: Ensure the API token has organization management permissions
2. **Network Errors**: Verify the selected stack matches your Keboola deployment
3. **Empty Data**: Check organization ID and ensure projects exist
4. **Permission Errors**: Verify token has sufficient permissions for user management

### Debug Information
The application provides debug information including:
- API endpoint URLs
- Request headers (with token sanitization)
- Response status codes
- Error messages from API calls
