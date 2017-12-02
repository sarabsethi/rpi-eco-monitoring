time=$1

# Schedule shutdown for set time
(sudo shutdown -c && sudo shutdown -r $time) &
