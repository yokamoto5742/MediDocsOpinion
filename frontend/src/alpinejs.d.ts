declare module 'alpinejs' {
    interface Alpine {
        data(name: string, callback: (...args: any[]) => any): void;
        start(): void;
    }

    const Alpine: Alpine;
    export default Alpine;
}
