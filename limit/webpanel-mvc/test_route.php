<?php
require 'vendor/autoload.php';
\ = require_once 'bootstrap/app.php';
\ = \->make(Illuminate\Contracts\Http\Kernel::class);
\ = \->handle(
    \ = Illuminate\Http\Request::create('/login', 'GET')
);
echo \->status();

