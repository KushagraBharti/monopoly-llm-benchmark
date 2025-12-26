import { type ButtonHTMLAttributes, type HTMLAttributes, forwardRef } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface NeoProps extends HTMLAttributes<HTMLDivElement> {
    variant?: 'default' | 'flat' | 'bordered';
}

export const NeoCard = forwardRef<HTMLDivElement, NeoProps>(
    ({ className, variant = 'default', children, ...props }, ref) => {
        return (
            <div
                ref={ref}
                className={cn(
                    "bg-white border-3 border-black p-4",
                    variant === 'default' && "shadow-neo",
                    variant === 'flat' && "shadow-none",
                    className
                )}
                {...props}
            >
                {children}
            </div>
        );
    }
);
NeoCard.displayName = "NeoCard";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
}

export const NeoButton = forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
        const variants = {
            primary: "bg-neo-green hover:bg-green-400 text-black",
            secondary: "bg-neo-yellow hover:bg-yellow-300 text-black",
            danger: "bg-neo-pink hover:bg-pink-400 text-white",
            ghost: "bg-transparent shadow-none border-2 border-black/20 hover:border-black hover:shadow-neo-sm hover:translate-x-0 hover:translate-y-0"
        };

        const sizes = {
            sm: "px-3 py-1 text-sm",
            md: "px-6 py-2 text-base",
            lg: "px-8 py-4 text-xl",
        };

        return (
            <button
                ref={ref}
                className={cn(
                    variants[variant],
                    sizes[size],
                    "font-bold uppercase tracking-wider transition-all active:translate-y-1 active:shadow-none border-3 border-black shadow-neo",
                    variant === 'ghost' && "shadow-none active:translate-y-0",
                    className
                )}
                {...props}
            />
        );
    }
);
NeoButton.displayName = "NeoButton";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
    variant?: 'neutral' | 'success' | 'warning' | 'error' | 'info';
}

export const NeoBadge = ({ className, variant = 'neutral', ...props }: BadgeProps) => {
    const variants = {
        neutral: "bg-gray-200 text-black",
        success: "bg-neo-green text-black",
        warning: "bg-neo-yellow text-black",
        error: "bg-neo-pink text-white",
        info: "bg-neo-cyan text-black",
    };

    return (
        <span
            className={cn(
                "inline-flex items-center px-2 py-0.5 border-2 border-black text-xs font-bold uppercase shadow-neo-sm",
                variants[variant],
                className
            )}
            {...props}
        />
    );
}
