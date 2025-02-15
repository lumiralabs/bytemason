// Root Layout
import './globals.css';
import Header from '@/components/shared/Header';
import Footer from '@/components/shared/Footer';

const RootLayout = ({ children }: { children: React.ReactNode }) => {
    return (
        <html lang="en">
            <body className="bg-gray-100">
                <Header />
                <main>{children}</main>
                <Footer />
            </body>
        </html>
    );
};

export default RootLayout;
