"""
utils/handler_loader.py
Handler loader module for aiogram 3.x with async/await support.
Provides automatic discovery and registration of handlers from modules.
"""

import asyncio
import importlib
import inspect
import logging
import os
import pkgutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type

from aiogram import Dispatcher, Router


class HandlerLoader:
    """
    Asynchronous handler loader for aiogram 3.x routers.
    Implements singleton pattern for efficient module loading.
    """
    
    _instance: Optional['HandlerLoader'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'HandlerLoader':
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize handler loader with caching mechanisms."""
        if not self._initialized:
            self.logger = logging.getLogger(__name__)
            self._loaded_modules: Set[str] = set()
            self._router_cache: Dict[str, Router] = {}
            self._initialized = True
            self.logger.info("HandlerLoader initialized")
    
    async def load_handlers_from_directory(
        self,
        directory: str,
        dp: Dispatcher,
        package_name: Optional[str] = None
    ) -> int:
        """
        Asynchronously load all handlers from a directory recursively.
        
        Args:
            directory: Path to the directory containing handler modules
            dp: Dispatcher instance to register routers
            package_name: Optional package name for relative imports
            
        Returns:
            Number of routers successfully loaded
            
        Raises:
            FileNotFoundError: If directory doesn't exist
            PermissionError: If directory access is denied
        """
        try:
            directory_path = Path(directory)
            if not directory_path.exists():
                raise FileNotFoundError(f"Directory not found: {directory}")
            
            if not directory_path.is_dir():
                raise ValueError(f"Path is not a directory: {directory}")
            
            self.logger.info("Loading handlers from directory: %s", directory)
            
            loaded_count = 0
            tasks = []
            
            # Walk through all Python files recursively
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        module_path = Path(root) / file
                        relative_path = module_path.relative_to(directory_path)
                        
                        # Convert path to module notation
                        module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')
                        if package_name:
                            full_module_name = f"{package_name}.{module_name}"
                        else:
                            full_module_name = module_name
                        
                        # Create async task for each module loading
                        task = self._load_module_async(full_module_name, dp)
                        tasks.append(task)
            
            # Execute all loading tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful loads
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error("Failed to load module: %s", result)
                elif result:
                    loaded_count += 1
            
            self.logger.info("Successfully loaded %d router(s) from %s", loaded_count, directory)
            return loaded_count
            
        except (FileNotFoundError, PermissionError, ValueError) as e:
            self.logger.error("Error loading handlers from directory %s: %s", directory, e)
            raise
    
    async def _load_module_async(self, module_name: str, dp: Dispatcher) -> bool:
        """
        Asynchronously load a single module and register its router.
        
        Args:
            module_name: Full module name to load
            dp: Dispatcher instance for registration
            
        Returns:
            True if module was loaded successfully, False otherwise
        """
        try:
            # Check if module is already loaded
            if module_name in self._loaded_modules:
                self.logger.debug("Module already loaded: %s", module_name)
                return True
            
            # Import module asynchronously
            module = await asyncio.to_thread(importlib.import_module, module_name)
            
            # Look for router instance in module
            router = None
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, Router) and not name.startswith('_'):
                    router = obj
                    break
            
            # If no router found, look for register_handlers function
            if router is None:
                register_func = getattr(module, 'register_handlers', None)
                if callable(register_func):
                    # Rate limiting - HTTP: Consider adding delay if needed
                    router = Router(name=module_name)
                    try:
                        if inspect.iscoroutinefunction(register_func):
                            await register_func(router)
                        else:
                            register_func(router)
                    except Exception as e:
                        self.logger.error("Error in register_handlers for %s: %s", module_name, e)
                        return False
            
            # Register router if found
            if router is not None:
                dp.include_router(router)
                self._loaded_modules.add(module_name)
                self._router_cache[module_name] = router
                self.logger.debug("Successfully loaded router from: %s", module_name)
                return True
            else:
                self.logger.warning("No router found in module: %s", module_name)
                return False
                
        except ImportError as e:
            self.logger.error("Import error for module %s: %s", module_name, e)
            return False
        except Exception as e:
            self.logger.error("Unexpected error loading module %s: %s", module_name, e)
            return False
    
    async def load_specific_modules(
        self,
        module_names: List[str],
        dp: Dispatcher
    ) -> int:
        """
        Load specific modules by name.
        
        Args:
            module_names: List of module names to load
            dp: Dispatcher instance for registration
            
        Returns:
            Number of successfully loaded modules
        """
        loaded_count = 0
        tasks = []
        
        for module_name in module_names:
            task = self._load_module_async(module_name, dp)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                self.logger.error("Failed to load specific module: %s", result)
            elif result:
                loaded_count += 1
        
        return loaded_count
    
    def get_loaded_modules(self) -> List[str]:
        """Get list of all loaded module names."""
        return list(self._loaded_modules)
    
    def get_router(self, module_name: str) -> Optional[Router]:
        """Get router instance by module name."""
        return self._router_cache.get(module_name)
    
    def clear_cache(self) -> None:
        """Clear all cached modules and routers."""
        self._loaded_modules.clear()
        self._router_cache.clear()
        self.logger.info("HandlerLoader cache cleared")


# Global instance for easy access
handler_loader = HandlerLoader()


async def setup_handlers(dp: Dispatcher, handlers_dir: str = "handlers") -> int:
    """
    Setup all handlers from handlers directory.
    
    Args:
        dp: Dispatcher instance
        handlers_dir: Path to handlers directory
        
    Returns:
        Number of routers loaded
    """
    try:
        # Load handlers from directory
        loaded_count = await handler_loader.load_handlers_from_directory(
            directory=handlers_dir,
            dp=dp,
            package_name=handlers_dir
        )
        
        # Additional manual registrations if needed
        # await handler_loader.load_specific_modules([
        #     'handlers.special_module',
        #     'handlers.another_module'
        # ], dp)
        
        return loaded_count
        
    except Exception as e:
        logging.error("Failed to setup handlers: %s", e)
        return 0
