<?php
$payload = json_decode( $_POST[ 'payload' ], true );
$repo = $payload[ 'repository' ][ 'full_name' ];
$number = $payload[ 'number' ];

exec( 'jsub -mem 512M ~/code/SuchABot/suchabot/sync.bash ' . escapeshellarg( $repo ) . ' ' . escapeshellarg( $number ) );
error_log( 'Sync for PR ' . $number . ' of Repo ' . $repo );
