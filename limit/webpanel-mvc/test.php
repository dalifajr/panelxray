<?php
$pdo = new PDO('sqlite:database/database.sqlite');
$stmt = $pdo->query('SELECT * FROM users');
print_r($stmt->fetchAll(PDO::FETCH_ASSOC));
