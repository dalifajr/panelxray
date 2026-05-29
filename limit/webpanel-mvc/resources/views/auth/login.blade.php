<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - VPN XRAY Panel</title>
    
    <!-- External Resources -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    
    <style>
        :root {
            --primary-color: #0d47a1;
            --primary-light: #1976d2;
            --accent-color: #ffd700;
            --text-dark: #1e293b;
            --text-muted: #64748b;
            --bg-color: #f1f5f9;
            --white: #ffffff;
            --radius-lg: 16px;
            --radius-md: 10px;
            --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(at 0% 0%, hsla(217,91%,60%,1) 0, transparent 50%), 
                radial-gradient(at 100% 100%, hsla(217,91%,60%,1) 0, transparent 50%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }

        .login-wrapper {
            width: 100%;
            max-width: 1200px;
            background: var(--white);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-xl);
            display: flex;
            overflow: hidden;
            min-height: 600px;
        }

        .login-section {
            flex: 1;
            padding: 4rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .brand-header {
            margin-bottom: 3rem;
        }

        .brand-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin: 0 0 0.5rem 0;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .brand-subtitle {
            font-size: 1.1rem;
            color: var(--text-muted);
            margin: 0;
        }

        .btn-primary {
            width: 100%;
            padding: 1.25rem 1rem;
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
            color: var(--white);
            border-radius: var(--radius-md);
            font-weight: 600;
            font-size: 1.1rem;
            cursor: pointer;
            border: none;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            transition: var(--transition);
            font-family: 'Outfit', sans-serif;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(13, 71, 161, 0.3);
        }

        .btn-telegram {
            background: #0088cc;
            color: white;
            margin-top: 1rem;
        }

        .btn-telegram:hover {
            background: #0077b5;
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-label {
            display: block;
            margin-bottom: 0.5rem;
            color: var(--text-dark);
            font-weight: 500;
        }

        .form-control {
            width: 100%;
            padding: 1rem;
            border: 1px solid #cbd5e1;
            border-radius: var(--radius-md);
            font-family: 'Outfit', sans-serif;
            font-size: 1rem;
            transition: var(--transition);
        }

        .form-control:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(13, 71, 161, 0.1);
        }

        .divider {
            display: flex;
            align-items: center;
            text-align: center;
            margin: 2rem 0;
            color: var(--text-muted);
        }

        .divider::before, .divider::after {
            content: '';
            flex: 1;
            border-bottom: 1px solid #cbd5e1;
        }

        .divider:not(:empty)::before {
            margin-right: .5em;
        }

        .divider:not(:empty)::after {
            margin-left: .5em;
        }

        .info-section {
            flex: 1.2;
            background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%);
            padding: 4rem;
            color: var(--white);
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .info-section::after {
            content: '';
            position: absolute;
            top: 0; right: 0; bottom: 0; left: 0;
            opacity: 0.1;
            background-image: radial-gradient(#fff 1px, transparent 1px);
            background-size: 20px 20px;
            pointer-events: none;
        }

        .info-title {
            font-size: 2.25rem;
            font-weight: 700;
            margin: 0 0 1rem 0;
            position: relative;
            z-index: 1;
        }

        .info-desc {
            font-size: 1.1rem;
            opacity: 0.8;
            line-height: 1.6;
            margin: 0 0 2rem 0;
            position: relative;
            z-index: 1;
        }

        .info-alert {
            background: rgba(255, 255, 255, 0.1);
            padding: 1.5rem;
            border-radius: var(--radius-md);
            backdrop-filter: blur(10px);
            position: relative;
            z-index: 1;
            display: flex;
            align-items: flex-start;
            gap: 1rem;
        }

        .info-alert i {
            color: var(--accent-color);
            font-size: 1.5rem;
            margin-top: 0.2rem;
        }

        .info-alert p {
            margin: 0;
            font-size: 0.95rem;
            line-height: 1.5;
        }

        .alert-error {
            background-color: #fee2e2;
            color: #991b1b;
            padding: 1rem;
            border-radius: var(--radius-md);
            margin-bottom: 2rem;
            font-size: 0.95rem;
            border: 1px solid #f87171;
        }

        .footer-text {
            text-align: center;
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-top: 3rem;
        }

        @media (max-width: 968px) {
            .login-wrapper { flex-direction: column; }
            .info-section { display: none; }
            .login-section { padding: 3rem 2rem; }
            body { padding: 1rem; }
        }
    </style>
</head>
<body>
    <div class="login-wrapper">
        <!-- Form Section -->
        <div class="login-section">
            <div class="brand-header">
                <h1 class="brand-title"><i class="fas fa-shield-alt"></i> VPN XRAY</h1>
                <p class="brand-subtitle">Panel Admin Server</p>
            </div>
            
            <div style="margin-bottom: 2rem;">
                <h2 style="color: var(--text-dark); font-size: 1.5rem; margin: 0 0 0.5rem 0; font-weight: 600;">Selamat Datang</h2>
                <p style="color: var(--text-muted); margin: 0;">Silakan login untuk mengakses panel.</p>
            </div>

            @if(session('error'))
            <div class="alert-error">
                <i class="fas fa-exclamation-circle" style="margin-right: 0.5rem;"></i> {{ session('error') }}
            </div>
            @endif

            <form action="{{ route('login.post') }}" method="POST">
                @csrf
                <div class="form-group">
                    <label class="form-label">Username</label>
                    <input type="text" name="username" class="form-control" required placeholder="Masukkan username">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-control" required placeholder="Masukkan password">
                </div>

                <button type="submit" class="btn-primary">
                    Login
                </button>
            </form>

            <div class="divider">ATAU</div>

            <a href="{{ route('auth.telegram') }}" class="btn-primary btn-telegram">
                <i class="fab fa-telegram-plane fs-5"></i> 
                <span>Login via Telegram</span>
            </a>

            <div style="text-align: center; margin-top: 1.5rem;">
                <p style="color: var(--text-muted);">Belum punya akun? <a href="{{ route('register') }}" style="color: var(--primary-color); font-weight: 600; text-decoration: none;">Daftar Sekarang</a></p>
            </div>
            
            <div class="footer-text">
                &copy; {{ date('Y') }} VPN Xray Panel. All rights reserved.
            </div>
        </div>

        <!-- Info Section -->
        <div class="info-section">
            @php
                $announcement = \App\Models\Setting::where('key', 'login_announcement')->value('value');
                if (!$announcement) {
                    $announcement = "Keamanan Terjamin\nLogin diotomatisasi melalui integrasi bot Telegram untuk memastikan hanya admin berwenang yang dapat mengakses kontrol panel server.";
                }
                $parts = explode("\n", str_replace("\r", "", $announcement), 2);
                $title = $parts[0] ?? 'Keamanan Terjamin';
                $desc = $parts[1] ?? 'Login diotomatisasi melalui integrasi bot Telegram untuk memastikan hanya admin berwenang yang dapat mengakses kontrol panel server.';
            @endphp
            <h2 class="info-title">{{ $title }}</h2>
            <p class="info-desc">
                {!! nl2br(e($desc)) !!}
            </p>
            <div class="info-alert">
                <i class="fas fa-info-circle"></i>
                <p>Klik tombol login, lalu mulai (start) bot untuk mendapatkan link akses masuk langsung ke dashboard.</p>
            </div>
        </div>
    </div>
</body>
</html>
