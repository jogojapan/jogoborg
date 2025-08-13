This is an example source directory for Jogoborg testing.

Replace this directory with your actual data to backup:
- Documents
- Configuration files  
- Application data
- Database volumes

Mount your real directories in docker-compose.yml:
volumes:
  - /home/user/documents:/sourcespace/documents:ro
  - /etc:/sourcespace/config:ro
  - /var/lib/docker/volumes:/sourcespace/docker-volumes:ro