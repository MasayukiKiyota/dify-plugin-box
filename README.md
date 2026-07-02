# Box Plugin for Dify

**Author:** MasayukiKiyota
**Version:** 0.0.1
**Type:** Tool

## Description

The Box plugin enables Dify applications to interact with Box files and folders. With this plugin, you can build AI applications that can list, search, upload, download, and manage files in Box.

## Features

- **List Files and Folders**: View the contents of any folder in your Box account
- **Search Files**: Find files and folders matching your search criteria
- **Upload Files**: Create new files in your Box account
- **Download Files**: Retrieve file content from your Box account
- **Create Folders**: Organize your Box account by creating new folders
- **Delete Files/Folders**: Remove files or folders from your Box account

## Working with Box IDs

Unlike some cloud storage services, Box addresses items by **numeric ID**, not by path:

- The **root folder** always has the ID `0`.
- Every file and folder has its own ID.

Use **List Files** (starting from the root folder `0`) or **Search Files** to discover the IDs of the items you want to operate on. Then pass those IDs to the other tools (download, upload target, create folder, delete).

## Setup

1. Install the plugin in your Dify workspace.
2. Create a Box application in the [Box Developer Console](https://app.box.com/developers).
   - Choose an **OAuth 2.0 (User Authentication)** app.
   - Add the redirect URI provided by Dify to your Box app's configuration.
   - Enable the "Write all files and folders" application scope so uploads, folder creation, and deletion work.
3. Copy the **Client ID** and **Client Secret** from your Box app.
4. In Dify, authorize the plugin using OAuth — you'll be redirected to Box to grant access.

## Authentication

This plugin uses **OAuth 2.0**. You provide your Box app's Client ID and Client Secret, then complete the OAuth flow in the browser. Dify securely stores the resulting access and refresh tokens and automatically refreshes the access token when it expires.

## Usage Examples

### List files in your Box root folder
```
List all files in my Box (folder 0)
```

### Search for specific files
```
Find all PDF files in my Box
```

### Upload a new file
```
Upload a file named "meeting-notes.txt" to my Box with the content "Meeting scheduled for next Tuesday"
```

### Download file content
```
Download the Box file with ID 123456789
```

### Create a folder
```
Create a folder named "Reports" in my Box root folder
```

### Delete an item
```
Delete the Box file with ID 123456789
```

## Requirements

- A Box account
- A Box OAuth 2.0 application (Client ID + Client Secret)
- Dify platform (version 1.9.0 or later)
