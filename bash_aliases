# Base system binaries
export PATH="/sbin:/bin:/usr/sbin:/usr/bin:/usr/syno/sbin:/usr/syno/bin:/usr/local/sbin:/usr/local/bin"

# Additional tools and libraries from opt
export PATH="$PATH:/opt/bin:/opt/sbin"

# Cargo and Rust binaries (for tools like eza)
export CARGO_HOME=/volume1/rust-install/.cargo
export RUSTUP_HOME=/volume1/rust-install/.rustup
export PATH="$CARGO_HOME/bin:$PATH"


# fzf for fuzzy finding capabilities
export PATH="$HOME/.fzf/bin:$PATH"

# Local bin for pip and other user-specific applications
export PATH="$PATH:$HOME/.local/bin"

# This is my current / up-to-date list of bash aliases.

# DOCKER - All Docker commands start with "d" AND Docker Compose commands start with "dc"
alias dstop='sudo docker stop $(sudo docker ps -a -q)' # usage: dstop container_name
alias dstopall='sudo docker stop $(sudo docker ps -aq)' # stop all containers
alias drm='sudo docker rm $(sudo docker ps -a -q)' # usage: drm container_name
alias dprunevol='sudo docker volume prune' # remove unused volumes
alias dprunesys='sudo docker system prune -a' # remove unsed docker data
alias ddelimages='sudo docker rmi $(sudo docker images -q)' # remove unused docker images
alias derase='dstopcont ; drmcont ; ddelimages ; dvolprune ; dsysprune' # WARNING: removes everything! 
alias dprune='ddelimages ; dprunevol ; dprunesys' # remove unused data, volumes, and images (perfect for safe clean up)
alias dexec='sudo docker exec -ti' # usage: dexec container_name (to access container terminal)
alias dps='sudo docker ps -a' # running docker processes
alias dpss='sudo docker ps -a --format "table {{.Names}}\t{{.State}}\t{{.Status}}\t{{.Image}}" | (sed -u 1q; sort)' # running docker processes as nicer table
alias ddf='sudo docker system df' # docker data usage (/var/lib/docker)
alias dlogs='sudo docker logs -tf --tail="50" ' # usage: dlogs container_name
alias dlogsize='sudo du -ch $(sudo docker inspect --format='{{.LogPath}}' $(sudo docker ps -qa)) | sort -h' # see the size of docker containers
alias dips="sudo docker ps -q | xargs -n 1 sudo docker inspect -f '{{.Name}}%tab%{{range .NetworkSettings.Networks}}{{.IPAddress}}%tab%{{end}}' | sed 's#%tab%#\t#g' | sed 's#/##g' | sort | column -t -N NAME,IP\(s\) -o $'\t'"

alias dp600='sudo chown -R root:root $HOME/docker/secrets ; sudo chmod -R 600 $HOME/docker/secrets ; sudo chown -R root:root $HOME/docker/.env ; sudo chmod -R 600 $HOME/docker/.env' # re-lock permissions
alias dp777='sudo chown -R $USER:$USER $HOME/docker/secrets ; sudo chmod -R 777 $HOME/docker/secrets ; sudo chown -R $USER:$USER $HOME/docker/.env ; sudo chmod -R 777 $HOME/docker/.env' # open permissions for editing

# DOCKER COMPOSE TRAEFIK 2 - All docker-compose commands start with "dc" 
alias dcrun='sudo COMPOSE_HTTP_TIMEOUT=200 docker-compose -f /volume1/docker/docker-compose.yml' # /volume1/docker symlinked to /var/services/homes/user/docker;;

alias dclogs='dcrun logs -tf --tail="50" ' # usage: dclogs container_name
alias dcup='dcrun up -d --build' # up the stack
alias dcdown='dcrun down --remove-orphans' # down the stack
alias dcrec='dcrun up -d --force-recreate --remove-orphans' # usage: dcrec container_name
alias dcstop='dcrun stop' # usage: dcstop container_name
alias dcrestart='dcrun restart ' # usage: dcrestart container_name
alias dcstart='dcrun start ' # usage: dcstart container_name
alias dcpull='dcrun pull' # usage: dcpull to pull all new images or dcpull container_name
alias traefiklogs='tail -f /volume1/docker/appdata/traefik2/traefik.log' # tail traefik logs

# NAVIGATION
alias cd..='cd ..'
alias ..='cd ..'
alias ...='cd ../..'
alias .3='cd ../../..'
alias .4='cd ../../../..'
alias .5='cd ../../../../..'

# SEARCH AND FIND
alias gh='history|grep' # search bash history
alias findr='sudo find / -name'
alias grep='grep --color=auto'
alias egrep='egrep --color=auto'
alias fgrep='fgrep --color=auto'

# TRASH - trash-cli
alias rm='trash-put'
alias rmv='rm -rv'
alias tempty='trash-empty ; sudo trash-empty ; sudo -H trash-empty'
alias tlist='trash-list'
alias srmt='sudo trash-put'

# FILE SIZE AND STORAGE
alias fdisk='sudo fdisk -l'
alias uuid='sudo vol_id -u'
alias ls='eza'
# alias ls='ls -F --color=auto --group-directories-first'
# alias ll='ls -alh --color=auto --group-directories-first'
# alias lt='ls --human-readable --color=auto --size -1 -S --classify' # file size sorted
# alias lsr='ls --color=auto -t -1' # recently modified
alias mnt='mount | grep -E ^/dev | column -t' # show mounted drives
alias dirsize='sudo du -hx --max-depth=1'
alias dirusage='du -ch | grep total' # Grabs the disk usage in the current directory
alias diskusage='df -hl --total | grep total' # Gets the total disk usage on your machine
alias partusage='df -hlT --exclude-type=tmpfs --exclude-type=devtmpfs' # Shows the individual partition usages without the temporary memory values
alias usage10='du -hsx * | sort -rh | head -10' # Gives you what is using the most space. Both directories and files. Varies on current directory

# NETWORKING
alias portsused='sudo netstat -tulpn | grep LISTEN'
alias showports='netstat -lnptu'
alias showlistening='lsof -i -n | egrep "COMMAND|LISTEN"'
alias ping='ping -c 5'
alias ipe='curl ipinfo.io/ip' # external ip
alias ipi='ipconfig getifaddr en0' # internal ip
alias header='curl -I' # get web server headers 

# SYNOLOGY DSM COMMANDS
alias servicelist='sudo synoservicecfg --list' # does not work in DSM 7
alias servicestatus='sudo synosystemctl status'
alias servicestop='sudo synosystemctl stop'
alias servicehstop='sudo synoservicecfg --hard-stop' # does not work in DSM 7
alias servicestart='sudo synosystemctl start'
alias servicehstart='sudo synoservicecfg --hard-start' # does not work in DSM 7
alias servicerestart='sudo synosystemctl restart'
alias restartdocker='sudo synosystemctl restart pkgctl-Docker'

# MISCELLANEOUS
alias wget='wget -c'
alias nano='sudo nano -iSw$'


# Use fzf to enhance the 'cd' command with fuzzy finding capabilities
# fcd() {
#   local dir
#   dir=$(find ${1:-.} -type d -not -path '*/\.*' 2> /dev/null | fzf +m) && cd "$dir"
# }

# [#  -f ~/.fzf.bash ] && source ~/.fzf.bash


alias cat='bat'
alias top='htop'