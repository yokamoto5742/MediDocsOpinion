declare module 'alpinejs' {
    interface Alpine {
        data(name: string, callback: () => any): void;
        start(): void;
    }

    const Alpine: Alpine;
    export default Alpine;
}
