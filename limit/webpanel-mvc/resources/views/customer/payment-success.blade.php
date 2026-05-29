@extends('layouts.app')

@section('content')
<div class="container-fluid py-4">
    <div class="row justify-content-center">
        <div class="col-md-8 col-lg-6">
            <div class="card shadow border-0 text-center">
                <div class="card-body p-5">
                    <div class="mb-4">
                        <i class="fas fa-check-circle text-success" style="font-size: 5rem;"></i>
                    </div>
                    <h2 class="fw-bold text-dark mb-3">Pembayaran Berhasil!</h2>
                    <p class="text-secondary mb-4">Terima kasih, pembayaran Anda telah kami terima dan pesanan Anda telah diproses.</p>

                    <div class="bg-light p-4 rounded text-start mb-4 border">
                        <h5 class="fw-bold border-bottom pb-2 mb-3">Detail Pesanan</h5>
                        <ul class="list-unstyled mb-0">
                            <li class="mb-2"><strong>Reference:</strong> {{ $transaction->reference }}</li>
                            <li class="mb-2"><strong>Tipe:</strong> {{ str_replace('_', ' ', strtoupper($transaction->type)) }}</li>
                            <li class="mb-2"><strong>Username VPN:</strong> {{ $meta['username'] ?? '-' }}</li>
                            <li class="mb-2"><strong>Protokol:</strong> {{ strtoupper($meta['protocol'] ?? '-') }}</li>
                            @if(isset($meta['days']))
                                <li class="mb-2"><strong>Masa Aktif:</strong> {{ $meta['days'] }} Hari</li>
                            @endif
                            <li class="mb-2"><strong>Total Dibayar:</strong> <span class="text-success fw-bold">Rp {{ number_format($transaction->total_amount, 0, ',', '.') }}</span></li>
                        </ul>
                    </div>

                    <a href="{{ route('vpn.index', $meta['protocol'] ?? 'vmess') }}" class="btn btn-primary px-4 py-2">
                        <i class="fas fa-list me-2"></i>Kembali ke Daftar Akun
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection
