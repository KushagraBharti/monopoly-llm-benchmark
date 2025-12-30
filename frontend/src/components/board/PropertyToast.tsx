import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useRef } from 'react';
import type { Space } from '@/net/contracts';
import { getGroupColor } from '@/domain/monopoly/colors';

interface PropertyToastProps {
    isVisible: boolean;
    space: Space;
    method: 'BOUGHT' | 'WON' | 'TRADED';
    price?: number | null;
    start: { x: number; y: number };
    target?: { x: number; y: number } | null;
    onComplete?: () => void;
}

export const PropertyToast = ({
    isVisible,
    space,
    method,
    price,
    start,
    target,
    onComplete,
}: PropertyToastProps) => {
    const groupColor = getGroupColor(space.group);
    const targetPos = target ?? { x: start.x + 140, y: start.y - 80 };
    const completedRef = useRef(false);

    const triggerComplete = () => {
        if (completedRef.current) return;
        completedRef.current = true;
        onComplete?.();
    };

    useEffect(() => {
        if (!isVisible) return;
        completedRef.current = false;
        const timer = window.setTimeout(triggerComplete, 1200);
        return () => window.clearTimeout(timer);
    }, [isVisible]);

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    className="fixed left-0 top-0 z-[70] pointer-events-none"
                    initial={{ opacity: 0, x: start.x, y: start.y, scale: 0.7 }}
                    animate={{ opacity: 1, x: targetPos.x, y: targetPos.y, scale: 0.95 }}
                    exit={{ opacity: 0, scale: 0.6 }}
                    transition={{ type: 'spring', stiffness: 180, damping: 20 }}
                    onAnimationComplete={triggerComplete}
                >
                    <div className="bg-white border-2 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] p-2 w-56 rounded-sm">
                        <div
                            className="w-full h-7 mb-2 border border-black flex items-center justify-center font-black uppercase text-[10px] tracking-tight"
                            style={{ backgroundColor: groupColor }}
                        >
                            {space.kind === 'PROPERTY' ? 'Title Deed' : space.name}
                        </div>

                        <div className="text-center">
                            <h3 className="text-[13px] font-black uppercase leading-tight mb-2 px-1">
                                {space.name}
                            </h3>

                            <div className="border-t border-black pt-1 mt-1 flex items-center justify-center gap-2">
                                <span className="text-[9px] font-bold bg-black text-white px-1.5 py-0.5 rounded-sm uppercase">
                                    {method}
                                </span>
                                {typeof price === 'number' ? (
                                    <span className="font-mono text-[11px] text-gray-700">${price}</span>
                                ) : null}
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};
