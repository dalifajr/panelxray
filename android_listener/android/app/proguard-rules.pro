# Keep app entrypoints referenced via AndroidManifest and WorkManager.
-keep class com.dalifajr.jualan_listener.PaymentNotificationListenerService { *; }
-keep class com.dalifajr.jualan_listener.BootCompletedReceiver { *; }
-keep class com.dalifajr.jualan_listener.worker.SendQueuedPaymentWorker { *; }
