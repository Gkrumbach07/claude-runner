#!/bin/bash

set -e

# Environment variables expected:
# SITE_NAME - Name of the static site (CR name)
# SOURCE_TYPE - git, docker, or url
# MINIO_ENDPOINT - MinIO endpoint
# MINIO_ACCESS_KEY - MinIO access key
# MINIO_SECRET_KEY - MinIO secret key
# BUILD_ENABLED - Whether to run build step
# BUILD_COMMAND - Build command to run
# BUILD_OUTPUT_DIR - Directory containing built files
# BUILD_IMAGE - Build container image (not used in this implementation)

echo "🚀 Starting static site build and upload process"
echo "Site: $SITE_NAME"
echo "Source type: $SOURCE_TYPE"
echo "Build enabled: $BUILD_ENABLED"

# Validate required environment variables
if [[ -z "$SITE_NAME" ]]; then
    echo "❌ ERROR: SITE_NAME environment variable is required"
    exit 1
fi

if [[ -z "$SOURCE_TYPE" ]]; then
    echo "❌ ERROR: SOURCE_TYPE environment variable is required"
    exit 1
fi

if [[ -z "$MINIO_ENDPOINT" ]]; then
    echo "❌ ERROR: MINIO_ENDPOINT environment variable is required"
    exit 1
fi

# Setup MinIO client
echo "🔧 Setting up MinIO client..."
mc alias set myminio "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"

# Function to download and extract source
download_source() {
    echo "📥 Downloading source..."
    
    case "$SOURCE_TYPE" in
        "git")
            echo "Cloning Git repository: $GIT_REPOSITORY"
            git clone --depth 1 --branch "${GIT_BRANCH:-main}" "$GIT_REPOSITORY" source
            if [[ -n "$GIT_PATH" && "$GIT_PATH" != "." ]]; then
                echo "Moving to subdirectory: $GIT_PATH"
                mv "source/$GIT_PATH"/* . || mv "source/$GIT_PATH"/.[^.]* . 2>/dev/null || true
                rm -rf source
            else
                mv source/* . || mv source/.[^.]* . 2>/dev/null || true
                rmdir source 2>/dev/null || true
            fi
            ;;
        "docker")
            echo "Extracting from Docker image: $DOCKER_IMAGE"
            # Create a temporary container and copy files
            CONTAINER_ID=$(docker create "$DOCKER_IMAGE")
            docker cp "$CONTAINER_ID:${DOCKER_PATH:-/app}" ./source
            docker rm "$CONTAINER_ID"
            mv source/* . || mv source/.[^.]* . 2>/dev/null || true
            rmdir source 2>/dev/null || true
            ;;
        "url")
            echo "Downloading from URL: $URL_ARCHIVE"
            wget -O archive.zip "$URL_ARCHIVE"
            unzip -q archive.zip
            rm archive.zip
            
            # If there's a specific path within the archive, move to it
            if [[ -n "$URL_PATH" && "$URL_PATH" != "." ]]; then
                if [[ -d "$URL_PATH" ]]; then
                    mv "$URL_PATH"/* . || mv "$URL_PATH"/.[^.]* . 2>/dev/null || true
                    rm -rf "$URL_PATH"
                fi
            fi
            ;;
        *)
            echo "❌ ERROR: Unsupported source type: $SOURCE_TYPE"
            exit 1
            ;;
    esac
    
    echo "✅ Source downloaded successfully"
    ls -la
}

# Function to build the site
build_site() {
    if [[ "$BUILD_ENABLED" == "true" ]]; then
        echo "🔨 Building site..."
        
        # Install dependencies if package.json exists
        if [[ -f "package.json" ]]; then
            echo "Installing npm dependencies..."
            npm ci --only=production
        fi
        
        # Run build command
        echo "Running build command: $BUILD_COMMAND"
        eval "$BUILD_COMMAND"
        
        # Move built files to output directory
        BUILD_OUTPUT_DIR=${BUILD_OUTPUT_DIR:-dist}
        if [[ -d "$BUILD_OUTPUT_DIR" ]]; then
            echo "Moving built files from $BUILD_OUTPUT_DIR to /output"
            cp -r "$BUILD_OUTPUT_DIR"/* /output/ || cp -r "$BUILD_OUTPUT_DIR"/.[^.]* /output/ 2>/dev/null || true
        else
            echo "❌ ERROR: Build output directory $BUILD_OUTPUT_DIR not found"
            exit 1
        fi
        
        echo "✅ Build completed successfully"
    else
        echo "📂 Copying source files directly (no build step)"
        cp -r ./* /output/ || cp -r ./.[^.]* /output/ 2>/dev/null || true
    fi
}

# Function to upload to MinIO
upload_to_minio() {
    echo "☁️ Uploading to MinIO..."
    
    cd /output
    
    # Ensure we have files to upload
    if [[ -z "$(ls -A .)" ]]; then
        echo "❌ ERROR: No files to upload"
        exit 1
    fi
    
    # Create site.zip for backup/deployment tracking
    echo "Creating site.zip archive..."
    zip -r site.zip . -x "*.DS_Store" "*.git*"
    
    # Upload site.zip to a special location
    mc cp site.zip "myminio/sites/.archives/${SITE_NAME}-$(date +%Y%m%d-%H%M%S).zip"
    
    # Remove the zip from the directory we're about to sync
    rm site.zip
    
    # Sync all files to the site directory
    echo "Syncing files to MinIO: sites/$SITE_NAME/"
    mc mirror --overwrite --remove . "myminio/sites/$SITE_NAME/"
    
    # Verify upload
    echo "Verifying upload..."
    mc ls "myminio/sites/$SITE_NAME/" | head -10
    
    echo "✅ Upload completed successfully"
}

# Function to create default index.html if none exists
create_default_index() {
    if [[ ! -f "/output/index.html" ]]; then
        echo "📄 Creating default index.html"
        cat > /output/index.html << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$SITE_NAME</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            color: #333;
        }
        .header {
            text-align: center;
            border-bottom: 1px solid #eee;
            padding-bottom: 2rem;
            margin-bottom: 2rem;
        }
        .status {
            background: #f0f9ff;
            border: 1px solid #0ea5e9;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
        .footer {
            text-align: center;
            color: #666;
            font-size: 0.9rem;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #eee;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 $SITE_NAME</h1>
        <p>Your static site is now live!</p>
    </div>
    
    <div class="status">
        <h2>✅ Deployment Successful</h2>
        <p>Your site has been successfully built and deployed to the static hosting platform.</p>
        <ul>
            <li><strong>Site Name:</strong> $SITE_NAME</li>
            <li><strong>Deployed:</strong> $(date)</li>
            <li><strong>Source Type:</strong> $SOURCE_TYPE</li>
        </ul>
    </div>
    
    <div class="content">
        <h2>Next Steps</h2>
        <p>Replace this default page by:</p>
        <ol>
            <li>Adding an <code>index.html</code> file to your source</li>
            <li>Updating your StaticSite resource to trigger a rebuild</li>
            <li>Your custom content will appear here automatically</li>
        </ol>
    </div>
    
    <div class="footer">
        <p>Powered by OpenShift Static Hosting Platform</p>
    </div>
</body>
</html>
EOF
    fi
}

# Main execution flow
main() {
    echo "📋 Build Summary:"
    echo "  Site Name: $SITE_NAME"
    echo "  Source Type: $SOURCE_TYPE"
    echo "  Build Enabled: ${BUILD_ENABLED:-false}"
    echo "  MinIO Endpoint: $MINIO_ENDPOINT"
    echo ""
    
    # Download source
    download_source
    
    # Build site
    build_site
    
    # Create default index if needed
    create_default_index
    
    # Upload to MinIO
    upload_to_minio
    
    echo ""
    echo "🎉 Static site deployment completed successfully!"
    echo "🌐 Your site should be available at:"
    echo "   https://$SITE_NAME.sites.apps.example.com"
    echo "   https://sites.apps.example.com/publish/$SITE_NAME/"
}

# Run main function
main "$@"