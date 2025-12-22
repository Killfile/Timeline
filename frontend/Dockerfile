FROM nginx:alpine

WORKDIR /usr/share/nginx/html

# Copy static files
COPY index.html .
COPY app.js .
COPY style.css .

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
