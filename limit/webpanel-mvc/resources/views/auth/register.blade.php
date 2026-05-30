<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - VPN XRAY Panel</title>
    
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

        .btn-primary:disabled {
            background: #94a3b8;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
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

        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 50px;
            height: 24px;
        }

        .toggle-switch input { 
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #cbd5e1;
            transition: .4s;
            border-radius: 34px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }

        input:checked + .slider {
            background-color: var(--primary-color);
        }

        input:checked + .slider:before {
            transform: translateX(26px);
        }

        .form-check {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-top: 1rem;
            margin-bottom: 2rem;
            padding: 1rem;
            background: #f8fafc;
            border-radius: var(--radius-md);
            border: 1px solid #e2e8f0;
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

        .alert-error {
            background-color: #fee2e2;
            color: #991b1b;
            padding: 1rem;
            border-radius: var(--radius-md);
            margin-bottom: 2rem;
            font-size: 0.95rem;
            border: 1px solid #f87171;
        }

        .username-status {
            font-size: 0.875rem;
            margin-top: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .status-available { color: #16a34a; }
        .status-taken { color: #dc2626; }

        @media (max-width: 968px) {
            .login-wrapper { flex-direction: column; }
            .info-section { display: none; }
            .login-section { padding: 3rem 2rem; }
            body { padding: 1rem; }
        }
    </style>
    @if(env('TURNSTILE_SITE_KEY'))
        <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
    @endif
</head>
<body>
    <div class="login-wrapper">
        <!-- Form Section -->
        <div class="login-section">
            <div class="brand-header">
                <h1 class="brand-title"><i class="fas fa-shield-alt"></i> VPN XRAY</h1>
                <p class="brand-subtitle">Daftar Akun Baru</p>
            </div>
            
            <div style="margin-bottom: 2rem;">
                <h2 style="color: var(--text-dark); font-size: 1.5rem; margin: 0 0 0.5rem 0; font-weight: 600;">Buat Akun</h2>
                <p style="color: var(--text-muted); margin: 0;">Silakan isi formulir di bawah ini.</p>
            </div>

            @if($errors->any())
            <div class="alert-error">
                <i class="fas fa-exclamation-circle" style="margin-right: 0.5rem;"></i> Ada kesalahan pada input Anda.
                <ul style="margin: 0.5rem 0 0 1.5rem; padding: 0;">
                    @foreach($errors->all() as $error)
                        <li>{{ $error }}</li>
                    @endforeach
                </ul>
            </div>
            @endif

            <form action="{{ route('register.post') }}" method="POST" id="registerForm">
                @csrf
                <div class="form-group">
                    <label class="form-label">Username</label>
                    <input type="text" name="username" id="usernameInput" class="form-control" required placeholder="Pilih username" autocomplete="off" value="{{ old('username') }}">
                    <div id="usernameStatus" class="username-status"></div>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-control" required placeholder="Buat password (min. 6 karakter)">
                </div>

                <div class="form-check">
                    <label class="toggle-switch">
                        <input type="checkbox" name="link_telegram" value="1" checked>
                        <span class="slider"></span>
                    </label>
                    <div>
                        <div style="font-weight: 500; color: var(--text-dark);">Tautkan dengan Telegram</div>
                        <div style="font-size: 0.85rem; color: var(--text-muted);">Izinkan login cepat dengan 1 klik via bot Telegram setelah mendaftar.</div>
                    </div>
                </div>
                @if(env('TURNSTILE_SITE_KEY'))
                    <div class="form-group mb-3" style="display: flex; justify-content: center; margin-bottom: 1.5rem;">
                        <div class="cf-turnstile" data-sitekey="{{ env('TURNSTILE_SITE_KEY') }}" data-theme="light"></div>
                    </div>
                @endif

                <button type="submit" class="btn-primary" id="submitBtn">
                    Daftar Sekarang
                </button>
            </form>

            <div style="text-align: center; margin-top: 2rem;">
                <p style="color: var(--text-muted);">Sudah punya akun? <a href="{{ route('login') }}" style="color: var(--primary-color); font-weight: 600; text-decoration: none;">Login di sini</a></p>
            </div>
        </div>

        <!-- Info Section -->
        <div class="info-section">
            <h2 class="info-title">Satu Klik untuk Masuk</h2>
            <p class="info-desc">
                Dengan menautkan akun Anda ke Telegram, Anda tidak perlu lagi mengingat password. Cukup satu klik untuk mengakses panel VPN Anda.
            </p>
            <img src="https://core.telegram.org/file/464001154/1/1l7kQ-k2l_A.135242/57da6b38c0316ec504" alt="Telegram integration" style="max-width: 200px; margin-top: 2rem; opacity: 0.9; border-radius: var(--radius-md);">
        </div>
    </div>

    <script>
        const usernameInput = document.getElementById('usernameInput');
        const usernameStatus = document.getElementById('usernameStatus');
        const submitBtn = document.getElementById('submitBtn');
        let timeout = null;

        usernameInput.addEventListener('input', function() {
            clearTimeout(timeout);
            const username = this.value.trim();

            if (username.length < 3) {
                usernameStatus.innerHTML = '';
                submitBtn.disabled = true;
                return;
            }

            usernameStatus.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Mengecek ketersediaan...';
            usernameStatus.className = 'username-status';
            submitBtn.disabled = true;

            timeout = setTimeout(() => {
                fetch(`{{ route('api.check-username-register') }}?username=${encodeURIComponent(username)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.available) {
                            usernameStatus.innerHTML = '<i class="fas fa-check-circle"></i> Username tersedia';
                            usernameStatus.className = 'username-status status-available';
                            submitBtn.disabled = false;
                        } else {
                            usernameStatus.innerHTML = '<i class="fas fa-times-circle"></i> Username sudah terdaftar';
                            usernameStatus.className = 'username-status status-taken';
                            submitBtn.disabled = true;
                        }
                    })
                    .catch(err => {
                        usernameStatus.innerHTML = '';
                        submitBtn.disabled = false;
                    });
            }, 500);
        });
    </script>
</body>
</html>
