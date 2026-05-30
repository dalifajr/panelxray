@extends('layouts.app')

@section('content')
<div class="container py-4">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card shadow-sm border-0">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h4 class="fw-bold mb-0 text-uppercase">Perpanjang Akun {{ strtoupper($protocol) }}</h4>
                </div>
                <div class="card-body p-4">
                    <p class="mb-4">Username: <strong>{{ $user }}</strong></p>

                    @if(session('error'))
                        <div class="alert alert-danger">{{ session('error') }}</div>
                    @endif
                    @if($errors->any())
                        <div class="alert alert-danger">
                            <ul class="mb-0">
                                @foreach($errors->all() as $error)
                                    <li>{{ $error }}</li>
                                @endforeach
                            </ul>
                        </div>
                    @endif

                    <form action="{{ route('vpn.renew.process', [$protocol, $user]) }}" method="POST">
                        @csrf
                        <div class="mb-4">
                            <label class="form-label fw-bold">Tambah Masa Aktif (Hari)</label>
                            <input type="hidden" name="days" id="expiredInput" value="30">
                            <div class="d-flex flex-wrap gap-2">
                                @foreach([1, 3, 7, 14, 30, 60] as $day)
                                    <button type="button" class="btn btn-outline-primary day-btn" data-days="{{ $day }}">{{ $day }} Hari</button>
                                @endforeach
                            </div>
                        </div>

                        @if(Auth::user()->role === 'customer')
                        <div class="mb-4">
                            <div class="alert alert-info border-0 shadow-sm mb-0">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="mb-1 fw-bold text-dark"><i class="fas fa-receipt me-2"></i>Total Tagihan</h6>
                                        <small class="text-dark">Harga dasar per 30 hari: Rp {{ number_format($basePrice ?? 0, 0, ',', '.') }}</small>
                                    </div>
                                    <h4 class="mb-0 fw-bold text-success" id="priceDisplay">Rp 0</h4>
                                </div>
                            </div>
                        </div>
                        @endif

                        @if($protocol !== 'ssh')
                        <div class="mb-3">
                            <label class="form-label fw-bold">Perbarui Quota (GB)</label>
                            <input type="number" name="quota" class="form-control" value="{{ $quota ?? 0 }}" min="0">
                            <div class="form-text">Masukkan 0 untuk unlimited. Nilai saat ini: {{ $quota ?? 0 }} GB</div>
                        </div>
                        @endif

                        @if(Auth::user()->role === 'admin')
                        <div class="mb-4">
                            <label class="form-label fw-bold">Perbarui Limit IP</label>
                            <div class="input-group">
                                <button class="btn btn-outline-secondary" type="button" onclick="decrementInput('renewLimitIpInput')">-</button>
                                <input type="number" name="limit_ip" id="renewLimitIpInput" class="form-control text-center" value="{{ $limit_ip ?? 1 }}" min="1">
                                <button class="btn btn-outline-secondary" type="button" onclick="incrementInput('renewLimitIpInput')">+</button>
                            </div>
                            <div class="form-text">Jumlah maksimal IP yang dapat login bersamaan. Nilai saat ini: {{ $limit_ip ?? 1 }}</div>
                        </div>
                        @else
                        <div class="mb-4">
                            <label class="form-label fw-bold">Perbarui Limit IP</label>
                            <div class="input-group">
                                <button class="btn btn-outline-secondary" type="button" onclick="decrementInput('renewLimitIpInput')">-</button>
                                <input type="number" name="limit_ip" id="renewLimitIpInput" class="form-control text-center" value="{{ $limit_ip ?? 1 }}" min="1" @if($maxIpLimit > 0) max="{{ $maxIpLimit }}" @endif>
                                <button class="btn btn-outline-secondary" type="button" onclick="incrementInput('renewLimitIpInput')">+</button>
                            </div>
                            <div class="form-text">
                                Nilai saat ini: {{ $limit_ip ?? 1 }}.
                                @if($maxIpLimit > 0)
                                    Maksimal {{ $maxIpLimit }} IP sesuai pengaturan admin.
                                @else
                                    Tidak ada batas maksimal dari admin.
                                @endif
                            </div>
                        </div>
                        @endif

                        <div class="d-grid gap-2">
                            <button type="submit" class="btn btn-info text-white btn-lg">Perpanjang Sekarang</button>
                            <a href="{{ route('vpn.index', $protocol) }}" class="btn btn-light">Batal</a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
window.decrementInput = function(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const min = parseInt(input.getAttribute('min')) || 1;
    let val = parseInt(input.value) || 1;
    if (val > min) {
        input.value = val - 1;
        input.dispatchEvent(new Event('input'));
        input.dispatchEvent(new Event('change'));
    }
};

window.incrementInput = function(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const maxAttr = input.getAttribute('max');
    const max = maxAttr ? parseInt(maxAttr) : Infinity;
    let val = parseInt(input.value) || 1;
    if (val < max) {
        input.value = val + 1;
        input.dispatchEvent(new Event('input'));
        input.dispatchEvent(new Event('change'));
    }
};

document.addEventListener('DOMContentLoaded', function() {
    // Pricing Logic
    const basePrice = {{ isset($basePrice) ? $basePrice : 0 }};
    const isCustomer = {{ Auth::user()->role === 'customer' ? 'true' : 'false' }};
    const ipPrice = {{ isset($ipPrice) ? $ipPrice : 0 }};
    const priceDisplay = document.getElementById('priceDisplay');
    const expiredInput = document.getElementById('expiredInput');
    const dayBtns = document.querySelectorAll('.day-btn');
    const limitIpInput = document.getElementById('renewLimitIpInput');

    function updatePrice(days) {
        expiredInput.value = days;
        dayBtns.forEach(btn => {
            if (parseInt(btn.dataset.days) === days) {
                btn.classList.add('active', 'btn-primary');
                btn.classList.remove('btn-outline-primary');
            } else {
                btn.classList.remove('active', 'btn-primary');
                btn.classList.add('btn-outline-primary');
            }
        });

        if (isCustomer && priceDisplay) {
            const ip = limitIpInput ? (parseInt(limitIpInput.value, 10) || 1) : 1;
            let total = Math.round((basePrice / 30) * days);
            total += ip > 1 ? (ipPrice * (ip - 1)) : 0;
            priceDisplay.textContent = 'Rp ' + new Intl.NumberFormat('id-ID').format(total);
        }
    }

    // Default select 30 days
    updatePrice(30);

    dayBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            updatePrice(parseInt(this.dataset.days));
        });
    });

    if (limitIpInput) {
        limitIpInput.addEventListener('input', function() {
            updatePrice(parseInt(expiredInput.value || '0', 10));
        });
    }
});
</script>
@endsection
