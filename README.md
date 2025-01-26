# Home Server Configuration on Synology DS920+

Welcome to my home server GitHub repository. This repository serves as a centralized hub for managing a powerful and comprehensive Docker-based home server hosted on a Synology DS920+ with 20 GB RAM, optimized for versatility and robustness. Here, you will find Docker Compose files and configurations for a wide range of applications catering to different needs from media serving to data management and security.
## System Overview 
- **Host** : Synology DS920+ 
- **RAM** : 20 GB 
- **Storage** : 1x18TB 
- **OS** : DSM 7.X 
- **Docker Compose Version** : 3.5 or higher
## Network Configuration

This setup does not require external network configurations outside of what is defined in the Docker Compose files. Custom network subnets can be modified as needed. Networks used include: 
- `traefik_network`: Main proxy network 
- `socket_proxy`: For Docker socket communications 
- `nextcloud`: Dedicated network for Nextcloud
- Additional application-specific networks as defined in the Docker Compose file.
## Key Services
### Core Services 
- **Traefik** : Reverse proxy and load balancer with automatic SSL certificate management. 
- **Authelia** : Full-featured authentication server providing 2FA and SSO. 
- **Portainer** : Docker container management. 
- **Socket-Proxy** : Secure proxy for Docker API.
### Monitoring and Logging 
- **Dozzle** : Real-time log monitoring. 
- **Glances** : System monitoring. 
- **QDirStat** : Visual directory statistics.
### Data and File Management 
- **Vaultwarden** : Secure password storage. 
- **Nextcloud** : Personal cloud storage and office solution. 
- **PhotoPrism** : Photo management and sharing. 
- **MariaDB and phpMyAdmin** : Database management solutions. 
- **Redis** : Advanced key-value store. 
- **Redis Commander** : Redis database management. 
- **FileBrowser** : Web-based file manager. 
- **Qdrant** : Vector search engine.
### Media Servers 
- **Plex** : Media streaming platform including `plextraktsync` for syncing watched status and `Tautulli` for monitoring and statistics. 
- **Overseerr** : Media request and management tool for Plex and Emby servers.
### Downloaders and Indexers 
- **Transmission with VPN** : Secure torrent downloading. 
- **NZBGet and SABnzbd** : Usenet downloading. 
- **Sonarr, Radarr, Lidarr, Readarr, Bazarr, Prowlarr** : Media management for TV shows, movies, music, books, and subtitles. 
- **Flaresolverr** : Solves CAPTCHAs and manages Cloudflare challenges.
### Media Conversion Tools 
- **Handbrake** : Video transcoding. 
- **MKVToolNix and MakeMKV** : Video editing and remuxing. 
- **Tdarr** : Automated media transcoding.
### Remote Access and Security 
- **Guacamole** : Clientless remote desktop gateway. 
- **WireGuard** : Simple and fast VPN that utilizes modern cryptography. 
- **Code-Server** : VS Code running in the browser.
### System Maintenance 
- **Watchtower** : Automatic updating of Docker containers. 
- **Docker-GC** : Garbage collection of unused Docker images and containers. 
- **Ofelia** : A job scheduler that is a replacement for cron. 
- **Cloudflare Companion** : Automatic CNAME creation for services.
### AI and Machine Learning 
- **Anything LLM** : Custom AI services tailored for personal use.
### Dashboards 
- **Homarr** : Customizable homepage for all your services.

## Bash Aliases
I use bash_aliases to simplify starting and stopping containers/stack. 

Here are some example alias commands:

- `dcup` - Start Docker Traefik 2 stack
- `dcdown` - Stop Docker Traefik 2 stack
- `dcrec` - Start or recreate a specific service or the full stack
- `dcstop` - Stop a specific service or the full stack
- `dcrestart` - Restart a specific service or the full stack
- `dclogs` - See real-time logs for the corresponding stack or service
- `dcpull` - Pull new images for the corresponding stack or service