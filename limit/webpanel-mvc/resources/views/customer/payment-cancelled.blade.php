@extends('layouts.app')

@section('content')
<div class="container-fluid py-4">
    <div class="row justify-content-center">
        <div class="col-md-8 col-lg-6">
            <div class="card shadow border-0 text-center">
                <div class="card-body p-5">
                    <div class="mb-4">
                        <i class="fas fa-times-circle text-danger" style="font-size: 5rem;"></i>
                    </div>
                    <h2 class="fw-bold text-dark mb-3">Pembayaran Dibatalkan</h2>
                    <p class="text-secondary mb-4">Pesanan Anda telah dibatalkan dan tidak dapat dilanjutkan.</p>

                    <div class="bg-light p-4 rounded text-start mb-4 border border-danger">
                        <h5 class="fw-bold border-bottom border-danger pb-2 mb-3 text-danger">Detail Pembatalan</h5>
                        <ul class="list-unstyled mb-0">
                            <li class="mb-2"><strong>Reference:</strong> {{ $transaction->reference }}</li>
                            <li class="mb-2"><strong>Tipe:</strong> {{ str_replace('_', ' ', strtoupper($transaction->type)) }}</li>
                            <li class="mb-2">
                                <strong>Alasan Batal:</strong> 
                                <span class="text-danger fw-bold">{{ $reason }}</span>
                            </li>
                        </ul>
                    </div>

                    <a href="{{ route('vpn.index', $meta['protocol'] ?? 'vmess') }}" class="btn btn-outline-secondary px-4 py-2">
                        <i class="fas fa-arrow-left me-2"></i>Kembali ke Daftar Akun
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection
